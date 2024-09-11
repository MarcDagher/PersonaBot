import ast
import streamlit as st
from app_helper_functions import display_knowledge_graph, display_extracted_traits_data, display_error_box

def display_knowledge_graph_page(session_state):
  
  num_queries_made = session_state.num_queries_made
  # Check if the model used the graph
  if num_queries_made > 0:
    
    for i in range(-1, -num_queries_made - 1, -1): # backward loop
      cypher_code = session_state.cypher_code_and_query_outputs[i]['cypher_code']
      output = session_state.cypher_code_and_query_outputs[i]['output']
      extracted_data = session_state.extracted_data[i]

      # print(f"\n\n\n---------- In graph page {i}: {type(ast.literal_eval(extracted_data))}")
      
      # Validate type of the output
      if isinstance(output, str):
        output = ast.literal_eval(output)

      # If output brought back results
      if len(output) > 0:
        st.markdown(f"""
                  <h1 style="font-size: 25px; text-align: center; background-color: #F0F2F6; border-radius:5px; padding: 10px; margin-bottom: 20px">
                    Knowledge Graph of Agent's Query {i + 2}
                  </h1>""",  unsafe_allow_html=True)
        
        # Knowledge Graph
        try:
          st.markdown(f"""
                      <p>
                        <strong style="font-size: 16px;">Cypher Code: </strong> 
                        <span style="font-size: 13px; background-color: #F0F2F6; padding: 3px 7px; border-radius: 2px; color: #17d10e ;">
                           <strong>{cypher_code}</strong>
                        </span>
                      </p>
                      """, unsafe_allow_html=True)
          graph = display_knowledge_graph(output)
          st.plotly_chart(graph)
        except:
          display_error_box(text="⚠️ Attempted to draw the graph, but the Agent returned an unexpected knowledge graph format. ⚠️")
        
        # Extracted Data Graph
        try:
          st.markdown(f"""
                  <h1 style="font-size: 25px; text-align: center; background-color: #F0F2F6; border-radius:5px; padding: 10px; margin-bottom: 20px">
                    Agent's Extracted Data From Knowledge Graph {i + 2}
                  </h1>""",  unsafe_allow_html=True)
          
          graph = display_extracted_traits_data(ast.literal_eval(extracted_data))
          st.plotly_chart(graph)
        except Exception as e:
          display_error_box(text="⚠️ Attempted to draw the graph, but the Agent returned an unexpected format. ⚠️")

      # If output is empty
      else:
        st.title("Agent used the graph but the output is empty")

  # If Agent didn't use the graph
  else:
    st.title("The Agent didn't use the knowledge graph.")
  
  return session_state