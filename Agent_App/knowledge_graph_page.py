import ast
import streamlit as st
from app_helper_functions import display_knowledge_graph, display_extracted_traits_data

def display_knowledge_graph_page(session_state):
  
  num_queries_made = session_state.num_queries_made
  # Check if the model used the graph
  if num_queries_made > 0:
    
    for i in range(-1, -num_queries_made - 1, -1): # backward loop
      cypher_code = session_state.cypher_code_and_query_outputs[i]['cypher_code']
      output = session_state.cypher_code_and_query_outputs[i]['output']
      extracted_data = session_state.extracted_data[i]

      print(f"\n\n\n---------- In graph page {i}: {type(ast.literal_eval(extracted_data))}")
      
      # Validate type of the output
      if isinstance(output, str):
        output = ast.literal_eval(output)

      # If output brought back results
      if len(output) > 0:
        st.title("We have a graph")

        try:
          st.write(f"Query {abs(i)}: `{cypher_code}`")
          graph = display_knowledge_graph(output)
          st.plotly_chart(graph)
        except:
          st.write(f"Attempted to draw the graph, but the Agent returned an unexpected knowledge graph format.")

        try:
          st.write(f"Extracted Traits")
          graph = display_extracted_traits_data(ast.literal_eval(extracted_data))
          st.plotly_chart(graph)
        except:
          st.write(f"Attempted to draw the graph, but the Agent returned an unexpected format.")


      # If output is empty
      else:
        st.title("Agent used the graph but the output is empty")

  # If Agent didn't use the graph
  else:
    st.title("The Agent didn't use the knowledge graph.")
  
  return session_state