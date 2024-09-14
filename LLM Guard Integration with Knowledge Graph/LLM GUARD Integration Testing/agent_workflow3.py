import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from typing import Dict, TypedDict, Annotated, List
import operator
import logging
from cryptography.fernet import Fernet
from py2neo import Graph
from llm_guard import scan_output, scan_prompt
from llm_guard.input_scanners import Anonymize, PromptInjection
from llm_guard.output_scanners import NoRefusal, Toxicity
from llm_guard.vault import Vault

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Connect to Neo4j graph
graph = Graph(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USERNAME'), os.getenv('NEO4J_PASSWORD')))

class AgentState(TypedDict):
    conversation: Annotated[List[HumanMessage | AIMessage], operator.add]
    tool_messages: List[List[HumanMessage | AIMessage]]
    cypher_code_and_query_outputs: Annotated[List[Dict], operator.add]
    extracted_data: Annotated[List[str], operator.add]
    query_is_unique: Dict
    num_queries_made: int
    is_safe: bool

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (HumanMessage, AIMessage)):
            return {
                "type": obj.__class__.__name__,
                "content": obj.content
            }
        return super().default(obj)

@tool
def query_graph(query: str):
    """Query from Neo4j knowledge graph using Cypher."""
    return graph.run(query).data()

class Agent:
    def __init__(self, model, tools, system):
        self.model = model
        self.tools = tools
        self.system = system
        self.encryption_key = Fernet.generate_key()
        self.fernet = Fernet(self.encryption_key)
        self.logger = logging.getLogger(__name__)
        self.vault = Vault()
        
        # Initialize LLM Guard scanners
        self.input_scanners = [
            Anonymize(self.vault),
            PromptInjection()
        ]
        self.output_scanners = [
            NoRefusal(),
            Toxicity()
        ]
        
        for scanner in self.input_scanners + self.output_scanners:
            self.logger.debug(f"Initialized scanner: {scanner.__class__.__name__}")
            self.logger.debug(f"Scanner parameters: {scanner.scan.__code__.co_varnames}")

    def encrypt_data(self, data: str) -> str:
        encrypted = self.fernet.encrypt(data.encode()).decode()
        self.logger.debug(f"Encrypted: {data[:20]}... to {encrypted[:20]}...")
        return encrypted

    def decrypt_data(self, encrypted_data: str) -> str:
        decrypted = self.fernet.decrypt(encrypted_data.encode()).decode()
        self.logger.debug(f"Decrypted: {encrypted_data[:20]}... to {decrypted[:20]}...")
        return decrypted

    def call_groq(self, state: AgentState):
        messages = state['conversation']
        
        if self.system:
            conversation = [HumanMessage(content=self.system)] + messages
        else:
            conversation = messages

        safe_conversation = []
        for message in conversation:
            content = message.content
            if isinstance(content, list):
                content = " ".join(str(item) for item in content)
            elif not isinstance(content, str):
                content = str(content)

            try:
                original_content = content
                for scanner in self.input_scanners:
                    content, is_valid, risk_score = scanner.scan(content)
                    if not is_valid and not (isinstance(scanner, Anonymize) and risk_score < 1.0):
                        self.logger.warning(f"Input failed security check: {content[:50]}...")
                        return {
                            'conversation': [AIMessage(content=self.encrypt_data("I'm sorry, but I can't process that input due to security concerns."))],
                            'is_safe': False
                        }
                
                if content != original_content:
                    self.logger.info(f"Input was modified for security: {content[:50]}...")
                
                safe_conversation.append(HumanMessage(content=content) if isinstance(message, HumanMessage) else AIMessage(content=content))
            except Exception as e:
                self.logger.error(f"Error during input scanning: {str(e)}")
                return {
                    'conversation': [AIMessage(content=self.encrypt_data("An error occurred while processing your input."))],
                    'is_safe': False
                }

        ai_response = self.model.invoke(safe_conversation)

        try:
            safe_output = ai_response.content
            for scanner in self.output_scanners:
                self.logger.debug(f"Applying scanner: {scanner.__class__.__name__}")
                scanner_params = scanner.scan.__code__.co_varnames
                self.logger.debug(f"Scanner parameters: {scanner_params}")
                
                scan_args = {'output': safe_output}
                if 'prompt' in scanner_params:
                    scan_args['prompt'] = safe_conversation[-1].content
                
                safe_output, is_valid, _ = scanner.scan(**scan_args)
                
                self.logger.debug(f"Scanner result - is_valid: {is_valid}")
                
                if not is_valid:
                    self.logger.warning(f"Output failed security check: {safe_output[:50]}...")
                    return {
                        'conversation': [AIMessage(content=self.encrypt_data("I apologize, but I can't provide that response due to security concerns."))],
                        'is_safe': False
                    }
        except Exception as e:
            self.logger.error(f"Error during output scanning: {str(e)}", exc_info=True)
            return {
                'conversation': [AIMessage(content=self.encrypt_data("An error occurred while processing the response."))],
                'is_safe': False
            }

        encrypted_response = self.encrypt_data(safe_output)
        return {
            'conversation': [AIMessage(content=encrypted_response)],
            'is_safe': True
        }

    def use_tool(self, state: AgentState):
        ai_message = state['conversation'][-1]
        if not hasattr(ai_message, 'additional_kwargs') or 'function_call' not in ai_message.additional_kwargs:
            return self.call_groq(state)

        function_call = ai_message.additional_kwargs['function_call']
        tool_name = function_call['name']
        tool_args = json.loads(function_call['arguments'])

        if tool_name not in self.tools:
            return self.call_groq(state)

        tool = self.tools[tool_name]
        result = tool(**tool_args)

        return {
            'tool_messages': [[HumanMessage(content=str(result))]],
            'num_queries_made': state['num_queries_made'] + 1
        }

    def recommend_careers(self, state: AgentState):
        if not state['extracted_data']:
            return self.call_groq(state)
        
        decrypted_data = self.decrypt_data(state['extracted_data'][-1])
        
        # Process the decrypted data and generate recommendations
        recommendations = f"Based on the extracted data: {decrypted_data}, here are some career recommendations..."
        
        encrypted_recommendations = self.encrypt_data(recommendations)
        return {
            'conversation': [AIMessage(content=encrypted_recommendations)],
            'num_queries_made': state['num_queries_made']
        }

def create_agent():
    model = ChatGroq(
        temperature=0,
        model_name="llama-3.1-70b-versatile",
        groq_api_key=os.getenv('GROQ_API_KEY')
    )

    tools = [query_graph]

    system = "You are a helpful assistant specializing in personality traits and career recommendations."

    agent = Agent(model=model, tools=tools, system=system)

    workflow = StateGraph(AgentState)

    workflow.add_node("personality_scientist", agent.call_groq)
    workflow.set_entry_point("personality_scientist")
    
    # Add a conditional edge based on the 'is_safe' flag
    workflow.add_conditional_edges(
        "personality_scientist",
        lambda x: "end" if not x["is_safe"] else "personality_scientist",
        {
            "end": END,
            "personality_scientist": "personality_scientist"
        }
    )

    return workflow, agent

def test_agent():
    workflow, agent = create_agent()

    input_message = "I love spending time with my friends"
    
    # Test encryption and decryption
    test_message = "This is a test message for encryption and decryption."
    encrypted = agent.encrypt_data(test_message)
    decrypted = agent.decrypt_data(encrypted)
    assert test_message == decrypted, "Encryption/decryption test failed!"
    logger.info("Encryption and decryption test passed successfully.")

    initial_state = AgentState(
        conversation=[HumanMessage(content=input_message)],
        tool_messages=[],
        cypher_code_and_query_outputs=[],
        extracted_data=[],
        query_is_unique={'status': True, 'index': None},
        num_queries_made=0,
        is_safe=True
    )
    
    logger.info("Starting agent test...")
    logger.info(f"Input: {input_message}")
    logger.info(f"Initial state: {initial_state}")
    logger.info("-------------------")
    
    compiled_agent = workflow.compile()
    
    for output in compiled_agent.stream(initial_state):
        logger.debug(f"Current output: {output}")
        if isinstance(output, Dict) and 'personality_scientist' in output:
            conversation = output['personality_scientist'].get('conversation', [])
            if conversation:
                last_message = conversation[-1]
                if isinstance(last_message, AIMessage):
                    logger.info(f"Encrypted response: {last_message.content[:50]}...")
                    try:
                        decrypted_content = agent.decrypt_data(last_message.content)
                        logger.info(f"Decrypted response: {decrypted_content[:50]}...")
                        logger.info(f"Agent: {decrypted_content}")
                    except Exception as e:
                        logger.error(f"Error decrypting message: {str(e)}")
                        logger.info(f"Agent (encrypted): {last_message.content}")
                    break
    
    logger.info("-------------------")
    logger.info("Test completed.")
    
if __name__ == "__main__":
    test_agent()