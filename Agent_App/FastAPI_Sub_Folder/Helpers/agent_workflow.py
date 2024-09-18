# LangChain
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage
from langchain.graphs import Neo4jGraph
from langchain_core.tools import tool

# LangGraph
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# LangSmith
from langsmith import traceable


# General Imports
import os
import ast
import operator
from pathlib import Path
from dotenv import load_dotenv
from typing import TypedDict, Annotated
from IPython.display import Image, display
from FastAPI_Sub_Folder.Helpers import prompts 

# LLM Guard Imports
from llm_guard import scan_output, scan_prompt
from llm_guard.input_scanners import Anonymize, PromptInjection, BanTopics
from llm_guard.output_scanners import NoRefusal, Toxicity, Sensitive, Relevance
from llm_guard.vault import Vault

# Logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connect to graph
success = load_dotenv()
print(f"\n\n-------- {success}")
load_dotenv()
os.environ["NEO4J_URI"] = os.getenv('NEO4J_URI')
os.environ["NEO4J_USERNAME"] = os.getenv('NEO4J_USERNAME')
os.environ["NEO4J_PASSWORD"] = os.getenv('NEO4J_PASSWORD')
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv('LANGCHAIN_TRACING_V2')
graph = Neo4jGraph()

# Create Agent's State
class AgentState(TypedDict):
    conversation: Annotated[list[AnyMessage], operator.add]
    tool_messages: list[list[AnyMessage]]
    cypher_code_and_query_outputs: Annotated[list[dict], operator.add]
    extracted_data: Annotated[list[str], operator.add]
    query_is_unique: dict
    num_queries_made: int

# Create the tool to be used by the Agent
@tool
def query_graph(query):
    """Query from Neo4j knowledge graph using Cypher."""
    return graph.query(query)

# Create Agent
class Agent:
    def __init__(self, model, tools, system):
        self.system = system
        self.tools = {t.name: t for t in tools}
        self.model = model.bind_tools(tools)

        graph = StateGraph(AgentState)
        memory = MemorySaver()

        graph.add_node("personality_scientist", self.call_groq)
        graph.add_node("graph_querying_tool", self.use_tool)
        graph.add_node("structure_queried_data", self.structure_queried_data)
        graph.add_node("extract_data", self.extract_data)
        graph.add_node("recommend_careers", self.recommend_careers)

        graph.add_conditional_edges("personality_scientist", self.validate_tool_call, {False: END, True: "graph_querying_tool"})

        graph.add_edge("graph_querying_tool", "structure_queried_data")
        graph.add_edge("structure_queried_data", "extract_data")
        graph.add_edge("extract_data", "recommend_careers")
        graph.add_edge("recommend_careers", END)
        graph.set_entry_point("personality_scientist")

        self.graph = graph.compile(checkpointer=memory)
        display(Image(self.graph.get_graph().draw_mermaid_png()))

        # LLM Guard setup
        self.vault = Vault()
        self.input_scanners = [
            Anonymize(self.vault),
            PromptInjection(),
            BanTopics(["explicit", "hate", "violence"], threshold=0.95)
        ]
        self.output_scanners = [
            NoRefusal(threshold=0.8),
            Toxicity(threshold=0.8), 
            Sensitive(threshold=0.7),
            Relevance(threshold=0.8)
        ]

    def scan_input(self, content):
        for scanner in self.input_scanners:
            content, is_valid, risk_score = scanner.scan(prompt=content)
            if not is_valid:
                logger.warning(f"Input failed security check: {content[:50]}...")
                return None
        return content

    def scan_output(self, output, prompt):
        for scanner in self.output_scanners:
            output, is_valid, _ = scanner.scan(output=output, prompt=prompt)
            if not is_valid:
                logger.warning(f"Output failed security check: {output[:50]}...")
                return None
        return output

    @traceable
    def call_groq(self, state: AgentState):
        messages = state['conversation']
        conversation = [SystemMessage(content=self.system)] + messages

        # Scan input
        safe_conversation = []
        for message in conversation:
            safe_content = self.scan_input(message.content)
            if safe_content is None:
                return {'conversation': [HumanMessage(content="I'm sorry, but I can't process that input due to security concerns.")], 'num_queries_made': 0}
            safe_conversation.append(SystemMessage(content=safe_content) if isinstance(message, SystemMessage) else HumanMessage(content=safe_content))

        ai_response = self.model.invoke(safe_conversation)

        # Scan output
        safe_output = self.scan_output(ai_response.content, safe_conversation[-1].content)
        if safe_output is None:
            return {'conversation': [HumanMessage(content="I apologize, but I can't provide that response due to security concerns.")], 'num_queries_made': 0}

        return {'conversation': [ai_response], 'num_queries_made': 0}

    def validate_tool_call(self, state: AgentState):
        ai_message = state['conversation'][-1]
        if hasattr(ai_message, 'tool_calls'):
            return len(ai_message.tool_calls) > 0
        else:
            # If the message doesn't have tool_calls, assume no tool call was made
            return False

    def use_tool(self, state: AgentState):
        tool_calls = state['conversation'][-1].tool_calls
        num_queries_made = state['num_queries_made']
        query_uniqueness_dict = {'status': True, 'index': None}
        results = []
        
        for tool in tool_calls:
            print(f"Calling: {tool['name']}")

            if not tool['name'] in self.tools:
                print("\n ....tool name not found in list of tools....")
                result = "tool name was not found in the list of tools, retry"
            elif tool['name'] == 'query_graph' and len(state['cypher_code_and_query_outputs']) > 0:
                print("\n ---- Tool Use Update ----> checking if query exists")
               
                previous_queries = []
                for i in range(len(state['cypher_code_and_query_outputs'])):
                    cypher = state['cypher_code_and_query_outputs'][i]['cypher_code']
                    previous_queries.append((f"index: {i}", cypher))
                
                query = tool['args']
                print(f"\n ---- Tool Use Update ----> previous queries: {previous_queries}, new_query: {query}")

                ai_response = self.model.invoke([
                SystemMessage(content=prompts.query_validator_prompt),
                HumanMessage(content=f"new cypher query: {query}. List of queries: {previous_queries}")
                ])
                
                print(f"\n---- Tool Use Update ----> ai_response: {ai_response}\n")
                
                if 'none' in ai_response.content.lower():
                    print(f"\n ---- Tool Use Update ----> new query")
                    try:
                        result = self.tools[tool['name']].invoke(tool['args'])
                        num_queries_made += 1
                    except ValueError as e:
                        result = f"ValueError occurred: {str(e)}"    
                else:
                    print(f"\n ---- Tool Use Update ----> query exists\n")
                    try:
                        index = int(ai_response.content)
                        result = state['cypher_code_and_query_outputs'][index]['output']
                        query_uniqueness_dict = {'status': False, 'index': index}
                    except:
                        result = "Something is wrong. Please make sure to give me the correct index and not an empty string."
            else:
                print(f"\n---- Tool Use Update ----> query is unique\n")
                try:
                    result = self.tools[tool['name']].invoke(tool['args'])
                    num_queries_made += 1
                except ValueError as e:
                    result = f"ValueError occurred: {str(e)}" 

            results.append(ToolMessage(tool_call_id=tool['id'], name=tool['name'], content=str(result)))

        print("Back to the model!")
        return {'tool_messages': [results], 'query_is_unique': query_uniqueness_dict, 'num_queries_made': num_queries_made}
    
    def structure_queried_data(self, state: AgentState):
        if state['query_is_unique']['status'] == True:
            tool_calls = state['conversation'][-1].additional_kwargs['tool_calls']
            query_output = state['tool_messages'][-1]

            structured_outputs = []
            for i in range(len(tool_calls)):
                cypher_code = ast.literal_eval(tool_calls[i]['function']['arguments'])['query']
                output = query_output[i].content
                
                if cypher_code:
                    structured_outputs.append({'cypher_code': cypher_code, 'output': output})

            return {'cypher_code_and_query_outputs': structured_outputs}
        else:
            print("Query already exists, skipping structure_queried_data step")
            return
    
    def extract_data(self, state: AgentState):
        if state['query_is_unique']['status'] == True:
            queried_data = []
            last_tool_message = state['tool_messages'][-1]
            for i in range(-1, -len(last_tool_message)-1, -1):
                cypher_code = state['cypher_code_and_query_outputs'][i]['cypher_code']
                output = state['cypher_code_and_query_outputs'][i]['output']
                queried_data.append(f"cypher code: {cypher_code}. output: {output}")
                
            prompt = [SystemMessage(content=self.system)] + state['conversation'] + [HumanMessage(content= prompts.extractor_prompt.format(queried_data=queried_data))]
        else:
            existing_output_index = state['query_is_unique']['index']
            queried_data = state['cypher_code_and_query_outputs'][existing_output_index]['output']
            prompt = [SystemMessage(content=self.system)] + state['conversation'] + [HumanMessage(content= prompts.extractor_prompt.format(queried_data=queried_data))]
        
        extracted_data = self.model.invoke(prompt)

        return {"extracted_data": [extracted_data]}

    def recommend_careers(self, state: AgentState):
        prompt = [SystemMessage(content=self.system)] + state['conversation']
        prompt = prompt + [HumanMessage(content= prompts.recommender_prompt.format(extracted_data=state['extracted_data'][-1]))]
        
        recommended_careers = self.model.invoke(prompt)
        
        # Scan output
        safe_output = self.scan_output(recommended_careers.content, prompt[-1].content)
        if safe_output is None:
            return {'conversation': [SystemMessage(content="I apologize, but I can't provide that response due to security concerns.")], 'tool_messages': []}
        
        return {'conversation': [SystemMessage(content=safe_output)], 'tool_messages': []}