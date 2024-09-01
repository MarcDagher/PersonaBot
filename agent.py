# LangChain
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage
from langchain.graphs import Neo4jGraph
from langchain_core.tools import tool

# LangGraph
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# General Imports
import os
import operator
from pathlib import Path
from dotenv import load_dotenv
from typing import TypedDict, Annotated # to construct the agent's state

# Connect to graph
dotenv_path = Path('./.env')
load_dotenv(dotenv_path=dotenv_path)
os.environ["NEO4J_URI"] = os.getenv('uri')
os.environ["NEO4J_USERNAME"] = os.getenv('user_name')
os.environ["NEO4J_PASSWORD"] = os.getenv('password')
graph = Neo4jGraph()

# Create the tool to be used by the Agent
@tool
def query_graph(query):
  """Query from Neo4j knowledge graph using Cypher."""
  return graph.query(query)


# Create Agent's State
class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add] # operator.add allows us to add messages instead of replacing them when the LLM's output is returned

# Create Agent
class Agent:

    def __init__(self, model, tools, system=""):
        self.system = system
        self.tools = {t.name: t for t in tools} # Save the tools' names that can be used
        self.model = model.bind_tools(tools) # Provide the name of the tools to the agent

        graph = StateGraph(AgentState) # initialize a stateful graph
        memory = MemorySaver()

        graph.add_node("llm", self.call_groq) # Add LLM node
        graph.add_node("action", self.take_action) # Add Tool node
        
        # The edge where the decision to use a tool is made
        graph.add_conditional_edges("llm", self.exists_action, {True: "action", False: END})
        
        # Create edge and set starting point of the graph
        graph.add_edge("action", "llm")
        graph.set_entry_point("llm")

        self.graph = graph.compile(checkpointer=memory) # Build graph
        

    # Check if an action exists by checking the last message in the state which is supposed to contain the tool's info
    def exists_action(self, state: AgentState):
        result = state['messages'][-1]
        return len(result.tool_calls) > 0

    # Get the LLM's response and update the Agent's State by adding the response to the messages
    def call_groq(self, state: AgentState):
        messages = state['messages']
        if self.system: messages = [SystemMessage(content=self.system)] + messages
        
        message = self.model.invoke(messages)
        return {'messages': [message]}

    # Search for the tool and use it
    def take_action(self, state: AgentState):
        tool_calls = state['messages'][-1].tool_calls
        results = []
        for t in tool_calls:
            print(f"Calling: {t}")
            
            # If tool not found
            if not t['name'] in self.tools: 
                print("\n ....tool name not found in list of tools....")
                result = "bad tool name, retry"  # instruct LLM to retry
            
            # If tool exists, use it
            else:
                result = self.tools[t['name']].invoke(t['args']) 

            # Save the message returned from the tool
            results.append(ToolMessage(tool_call_id=t['id'], name=t['name'], content=str(result)))

        print("Back to the model!")
        return {'messages': results}