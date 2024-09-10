## FastAPI
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

## LangChain
from langchain_groq import ChatGroq
from langchain.graphs import Neo4jGraph
from langchain_core.messages import HumanMessage

## LangGraph
import agent_workflow

## Environment Variables
import os
import prompts
from pathlib import Path
from dotenv import load_dotenv

#############################
# Get environment variables #
#############################
dotenv_path = Path('../.env')
load_dotenv(dotenv_path=dotenv_path)
os.environ["GROQ_API_KEY"] = os.getenv('GROQ_API_KEY')

os.environ["NEO4J_URI"] = os.getenv('uri')
os.environ["NEO4J_USERNAME"] = os.getenv('user_name')
os.environ["NEO4J_PASSWORD"] = os.getenv('password')
graph = Neo4jGraph()

##############################
# Initialize model and agent #
##############################
model = ChatGroq(temperature=0.7, groq_api_key=os.environ["GROQ_API_KEY"], model_name="llama-3.1-70b-versatile")
# model = ChatGroq(temperature=0.7, groq_api_key=os.environ["GROQ_API_KEY"], model_name="llama3-70b-8192")
agent = agent_workflow.Agent(
    model=model, 
    tools=[agent_workflow.query_graph], 
    system=prompts.personality_scientist_prompt.format(schema=graph.structured_schema)
    )

# Function to send a message to groq and recive its outputs
def send_user_message(user_message):
    config = {"configurable": {"thread_id": "1"}}
    response = []
    for event in agent.graph.stream({"conversation": [user_message]}, config, stream_mode="values"):
        response.append(event["conversation"][-1].content)
    return {"response": response}


##################
# Initialize app #
##################
app = FastAPI()

class Messages(BaseModel):
    message: str


@app.post("/messages/")
async def call_agent(request: Messages):
    try:
        user_message = HumanMessage(content=request.message)
        ai_response = send_user_message(user_message)
        return ai_response
    except Exception as e:
        
        print("-----------------")
        print(e)
        print("-----------------")
        if e.response.status_code == 422: return "Unprocessable Entry"
        if e.response.status_code == 429: return "Rate limit reached for model"
        elif e.response.status_code == 500: return "Internal Server Error"
        elif e.response.status_code == 503: return "Internal Server Error"

# Only run this if the script is executed directly (not inside a notebook or interactive shell)
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)