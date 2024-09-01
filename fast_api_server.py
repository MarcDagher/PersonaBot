## FastAPI
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

## LangChain
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langchain.graphs import Neo4jGraph

## LangGraph
from agent import Agent, query_graph

## Environment Variables
import os
from pathlib import Path
from dotenv import load_dotenv

#############################
# Get environment variables #
#############################
dotenv_path = Path('./.env')
load_dotenv(dotenv_path=dotenv_path)
os.environ["GROQ_API_KEY"] = os.getenv('GROQ_API_KEY')

os.environ["NEO4J_URI"] = os.getenv('uri')
os.environ["NEO4J_USERNAME"] = os.getenv('user_name')
os.environ["NEO4J_PASSWORD"] = os.getenv('password')
graph = Neo4jGraph()

############################
# Construct Initial Prompt #
############################
task = "Task: You are a career guide. Your job is to ask me up to 3 questions to uncover my personality traits according to the RAISEC model. You will ask these questions in a conversational flow where you will ask the second question after I answer the first. Once you understand my personality, you will stop asking questions and use a Neo4j database to improve your knowledge on compatible career paths for me. You will query the possible occupation titles that are suitable for my character. At any point, I can ask you questions and you will answer normally, then you will continue your personality test."

goal = "Understand my personality/character and then suggest suitable career paths. Note: when asking your questions, please number them to keep track of the number of questions asked."

schema_context = f"Here is the graph's schema: {graph.structured_schema}."

property_values = f"Property Values: empty"

query_approach = "Querying approach: You will not use 'LIMIT'. If Property Values: empty, you will not use general queries and will not include 'WHERE' or try to specify property values inside your Cypher code."

output = "Your final output: Interpret all the queried data, choose up to 3 suitable careers for me, list them in bullet points and include a brief explanation of how each path suites my personality. Include Cypher code in your answer."

tone = "Output's tone: Make your output friendly, fun and easy to read."


reminder = "Reminder: If Property Values: empty, you will not use 'WHERE' or try to specify property values inside your Cypher code. Under no circumstances should you use 'DELETE'. Find the occupations that suite my character. Make sure to keep your answers concise and straight to the point."

prompt = f"{task}\ {goal}\ {schema_context}\ {property_values}\ {query_approach}\ {output}\ {tone}\ {reminder}"

##############################
# Initialize model and agent #
##############################
model = ChatGroq(temperature=0.5, groq_api_key=os.environ["GROQ_API_KEY"], model_name="llama-3.1-70b-versatile")
agent = Agent(model, [query_graph], system=prompt)

# Function to send a message to groq and recives its outputs
def send_user_message(user_message):
    config = {"configurable": {"thread_id": "1"}}
    response = []
    for event in agent.graph.stream({"messages": [user_message]}, config, stream_mode="values"):
        response.append(event["messages"][-1].content)
            
    return {"response": response}

##################
# Initialize app #
##################
app = FastAPI()

class QueryRequest(BaseModel):
    query: str

# Create route
@app.post("/query/")
async def query_model(request: QueryRequest):
    try:
        user_message = HumanMessage(content=request.query)
        ai_response = send_user_message(user_message)
        return ai_response
    except Exception as e:
        
        print("-----------------")
        print(e)
        print("-----------------")
        if e.response.status_code == 422: return "Unprocessable Entry"
        elif e.response.status_code == 500: return "Internal Server Error"
        elif e.response.status_code == 503: return "Internal Server Error"

# Only run this if the script is executed directly (not inside a notebook or interactive shell)
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)