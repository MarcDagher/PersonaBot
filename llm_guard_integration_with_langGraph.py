# Imports
import os
from pathlib import Path
from typing import TypedDict, Annotated
import operator

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langchain.graphs import Neo4jGraph
from langchain_core.tools import tool

from llm_guard import scan_prompt, scan_output
from llm_guard.input_scanners import Anonymize, PromptInjection, Toxicity
from llm_guard.output_scanners import Relevance
from llm_guard.vault import Vault

# Environment setup
def load_environment_variables():
    load_dotenv()
    os.environ["NEO4J_URI"] = os.getenv('NEO4J_URI')
    os.environ["NEO4J_USERNAME"] = os.getenv('NEO4J_USERNAME')
    os.environ["NEO4J_PASSWORD"] = os.getenv('NEO4J_PASSWORD')
    print('os.environ["NEO4J_URI"]: ' + os.environ["NEO4J_URI"])

# Neo4j graph setup
def setup_neo4j_graph():
    return Neo4jGraph()

# Tool definition
@tool
def query_graph(query: str) -> str:
    """Query the Neo4j knowledge graph using Cypher."""
    print('Executing query:', query)
    graph = setup_neo4j_graph()
    return str(graph.query(query))

# Agent state definition
class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]

# Agent class
class Agent:
    def __init__(self, model, tools, system=""):
        self.system = system
        self.tools = {t.name: t for t in tools}
        self.model = model.bind_tools(tools)
        self.graph = self._setup_graph()

    def _setup_graph(self):
        graph = StateGraph(AgentState)
        memory = MemorySaver()

        graph.add_node("llm", self.call_groq)
        graph.add_node("action", self.take_action)
        
        graph.add_conditional_edges("llm", self.exists_action, {True: "action", False: END})
        
        graph.add_edge("action", "llm")
        graph.set_entry_point("llm")

        return graph.compile(checkpointer=memory)

    def call_groq(self, state: AgentState):
        messages = state['messages']
        if self.system:
            messages = [SystemMessage(content=self.system)] + messages
        
        sanitized_messages = []
        for message in messages:
            content = str(message.content) if not isinstance(message.content, list) else " ".join(map(str, message.content))
            sanitized_messages.append(message.__class__(content=content))
        
        try:
            message = self.model.invoke(sanitized_messages)
        except Exception as e:
            return {'messages': [SystemMessage(content="Error during model processing.")]}
        
        return {'messages': [message]}

    def exists_action(self, state: AgentState):
        if not state['messages']:
            return False
        result = state['messages'][-1]
        has_tool_calls = hasattr(result, 'tool_calls') and len(result.tool_calls) > 0
        return has_tool_calls

    def take_action(self, state: AgentState):
        tool_calls = state['messages'][-1].tool_calls
        results = []
        for t in tool_calls:
            if t['name'] not in self.tools:
                result = "Tool not found, please try again"
            else:
                try:
                    result = self.tools[t['name']].invoke(t['args'])
                except Exception as e:
                    result = f"Error during tool execution: {str(e)}"
            results.append(HumanMessage(content=f"Tool {t['name']} returned: {result}"))
        
        return {'messages': results}


# Main execution
def generate_output(user_input):
    load_environment_variables()
    graph = setup_neo4j_graph()

    task = "Task: You are a career guide. Your job is to ask me up to 15 questions to uncover my personality traits according to the RAISEC model. You will ask these questions in a conversational flow where you will ask the second question after I answer the first. Once you understand my personality, you will stop asking questions and use a Neo4j database to improve your knowledge on compatible career paths for me. You will query the possible occupation titles that are suitable for my character. At any point, I can ask you questions and you will answer normally, then you will continue your personality test."

    goal = "Understand my personality and then suggest suitable career paths. Note: when asking your questions, please number them to keep track of the number of questions asked."

    schema_context = f"Here is the graph's schema: {graph.structured_schema}."

    property_values = f"Property Values: empty"

    query_approach = "Querying approach: You will not use 'LIMIT'. If Property Values: empty, you will not use general queries and will not include 'WHERE' or try to specify property values inside your Cypher code."

    output = "Your final output: Interpret all the queried data, choose up to 15 suitable careers for me, list them in bullet points and include a brief explanation of how each path suites my personality. Include Cypher code in your answer."

    tone = "Output's tone: Make your output friendly, fun and easy to read."

    personal_info = "Personal Info: I love people and I am a good listener. I enjoy observation and analysis. I prefer being with adults rather than with kids and I also have computer programming skills."

    reminder = "Reminder: If Property Values: empty, you will not use 'WHERE' or try to specify property values inside your Cypher code. Under no circumstances should you use 'DELETE'. Find the occupations that suite my character."

    prompt = f"{task} | {goal} | {schema_context} | {property_values} | {query_approach} | {output} | {tone} | {personal_info} | {reminder}"

    model = ChatGroq(
        temperature=0, 
        groq_api_key=os.environ["GROQ_API_KEY"], 
        model_name="llama-3.1-70b-versatile"
    )

    agent = Agent(model, [query_graph], system=prompt)

    config = {"configurable": {"thread_id": "1"}}
    input_message = HumanMessage(content=user_input)
    for event in agent.graph.stream({"messages": [input_message]}, config, stream_mode="values"):
        event["messages"][-1].pretty_print()

if __name__ == "__main__":
    generate_output('What will we do today?')
