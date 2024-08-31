import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from langchain_groq import ChatGroq
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from typing import Any, Dict, List
from pydantic import Field, BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential
import re

# Environment setup
def load_environment_variables():
    load_dotenv()
    required_vars = ["NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD", "GROQ_API_KEY"]
    for var in required_vars:
        if not os.getenv(var):
            raise EnvironmentError(f"{var} is not set in the environment or .env file")
    print(f"Neo4j URI: {os.getenv('NEO4J_URI')}")

# Neo4j graph setup
class Neo4jGraph:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def query(self, query, params=None):
        with self.driver.session() as session:
            result = session.run(query, params)
            return [dict(record) for record in result]

    def get_schema(self):
        schema_query = """
        CALL apoc.meta.schema()
        YIELD value
        RETURN value
        """
        result = self.query(schema_query)
        return result[0]['value'] if result else {}

def preprocess_cypher_query(query):
    # Replace spaces in node labels with underscores
    query = re.sub(r'(:|\()\s*([A-Za-z\s]+)\s*(:|\))', lambda m: f"{m.group(1)}{m.group(2).replace(' ', '_')}{m.group(3)}", query)
    
    # Ensure node labels start with an uppercase letter
    query = re.sub(r'(:|\()([a-z])', lambda m: f"{m.group(1)}{m.group(2).upper()}", query)
    
    return query

def clean_and_validate_cypher(raw_cypher: str) -> str:
    # Remove any markdown code block syntax
    cleaned_cypher = re.sub(r'```(?:cypher)?\s*|\s*```', '', raw_cypher).strip()
    
    # Ensure the query starts with a valid Cypher clause
    if not re.match(r'^(MATCH|OPTIONAL MATCH|CALL|CREATE|MERGE|DELETE|SET|REMOVE|FOREACH|WITH|UNWIND|START|RETURN)', cleaned_cypher, re.IGNORECASE):
        raise ValueError("No valid Cypher query found in the generated text.")
    
    # Ensure the query ends with a RETURN clause
    if not re.search(r'\bRETURN\b', cleaned_cypher, re.IGNORECASE):
        cleaned_cypher += " RETURN *"
    
    return cleaned_cypher

class CustomGraphCypherQAChain:
    def __init__(self, graph: Neo4jGraph, cypher_generation_chain: LLMChain, qa_chain: LLMChain):
        self.graph = graph
        self.cypher_generation_chain = cypher_generation_chain
        self.qa_chain = qa_chain

    def run(self, query: str) -> Dict[str, str]:
        graph_schema = self.graph.get_schema()
        # Generate Cypher
        cypher_generation_inputs = {
            "query": query,
            "schema": graph_schema,
        }
        raw_cypher = self.cypher_generation_chain.run(cypher_generation_inputs)

        try:
            cleaned_cypher = clean_and_validate_cypher(raw_cypher)
            print(f"Cleaned Cypher query: {cleaned_cypher}")
            context = self.graph.query(cleaned_cypher)
        except Exception as e:
            print(f"Error in Cypher query: {str(e)}")
            print(f"Problematic raw Cypher output: {raw_cypher}")
            context = f"Error in querying the database: {str(e)}"

        # Generate Answer
        answer_generation_inputs = {
            "query": query,
            "context": context,
        }
        answer = self.qa_chain.run(answer_generation_inputs)

        return {"result": answer}
    
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def query_knowledge_graph(uri, user, password, user_input):
    # Create a graph object for the CustomGraphCypherQAChain
    graph = Neo4jGraph(uri, user, password)
    
    # Initialize the LLM
    llm = ChatGroq(temperature=0, groq_api_key=os.environ["GROQ_API_KEY"], model_name="llama-3.1-8b-instant", max_tokens=None)
    
    # Construct Prompts
    cypher_prompt = PromptTemplate(
        input_variables=["schema", "query"],
        template="""
        Given the following schema and user query, generate a simple and focused Cypher query to extract relevant information from the Neo4j database:

        Schema: {schema}
        User Query: {query}

        Guidelines for generating the Cypher query:
        1. Focus on the main entities and relationships directly related to the user's query.
        2. Limit the query to 2-3 main node types and their immediate relationships.
        3. Use MATCH for required patterns and OPTIONAL MATCH sparingly for additional information.
        4. Avoid using LIMIT unless specifically needed.
        5. Return a focused set of properties that are most relevant to answering the query.
        6. Keep the query concise and avoid overly complex patterns.
        7. Do not include any explanations or comments, just the Cypher query itself.
        8. Use 'WHERE' clauses only if specific property values are mentioned in the user query.
        9. Do not wrap the query in markdown code blocks or backticks.

        Generate a Cypher query following these guidelines:
        """
    )
    
    answer_prompt = PromptTemplate(
        input_variables=["query", "context"],
        template="""
        Based on the user query: {query}
        And the context from the knowledge graph: {context}
        Provide a comprehensive answer:
        1. Interpret the queried data.
        2. If applicable, suggest up to 3 suitable careers based on the information, listing them in bullet points.
        3. Include a brief explanation of how each career path suits the user's personality or interests.
        4. Make your response friendly, engaging, easy to read, and well-structured.
        5. Keep your answer concise and to the point.
        6. If you used the knowledge graph to get your data, mention it.
        Answer:
        """
    )
    
    cypher_chain = LLMChain(llm=llm, prompt=cypher_prompt)
    qa_chain = LLMChain(llm=llm, prompt=answer_prompt)
    
    # Create the custom chain
    chain = CustomGraphCypherQAChain(
        graph=graph,
        cypher_generation_chain=cypher_chain,
        qa_chain=qa_chain
    )
    
    try:
        response = chain.run(user_input)
        result = response["result"]
    except Exception as e:
        print(f"Error occurred while querying the knowledge graph: {str(e)}")
        result = "I apologize, but I encountered an error while trying to process your request. Could you please rephrase your question or try a different query?"
    
    graph.close()
    return result

def main():
    try:
        # Load environment variables
        load_environment_variables()
        
        # Get Neo4j connection details
        neo4j_uri = os.getenv('NEO4J_URI')
        neo4j_user = os.getenv('NEO4J_USERNAME')
        neo4j_password = os.getenv('NEO4J_PASSWORD')
        
        while True:
            user_input = input("\nWrite your mind (or type 'exit' to quit): ").strip()
            
            if user_input.lower() == 'exit':
                print("Thank you for using the system. Goodbye!")
                break
            
            try:
                result = query_knowledge_graph(neo4j_uri, neo4j_user, neo4j_password, user_input)
                print("\nAnswer:", result)
            except Exception as e:
                print(f"An error occurred while processing your question: {str(e)}")
                print("Please try rephrasing your question or ask something else.")
    
    except Exception as e:
        print(f"An error occurred while setting up the system: {str(e)}")
        print("Please check your environment variables and Neo4j connection details.")

if __name__ == "__main__":
    main()
