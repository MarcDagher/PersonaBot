import ast
import streamlit as st
from app_helper_functions import create_plotly_graph

def display_knowledge_graph_page(session_state):
  if session_state.num_queries_made > 0:
    output = ast.literal_eval(session_state.cypher_code_and_query_outputs[-1]['output'])

    if len(output) > 0:
      print(f"\n\n\n---------- In graph page: {type(output)}")
      # print(f"\n\n\n---------- In graph page: {session_state.num_queries_made}")
      # print(f"\n\n\n---------- In graph page: {session_state.cypher_code_and_query_outputs[1]}")
      st.title("We have a graph")
      graph = create_plotly_graph(ast.literal_eval(output))
      
      st.plotly_chart(graph)
    
    else:
      st.title("El Agent Tole3 7mar")

  else:
    st.title("Ain't no graph yet")
  
  return session_state