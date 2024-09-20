import ast
import streamlit as st
from Streamlit_Sub_Folder.Helpers.app_helper_functions import display_knowledge_graph, display_extracted_traits_data, display_error_box

def display_knowledge_graph_page(session_state):
  
  # NOTE: session_state.graph_data_to_be_used => is a list of cypher codes that the Agent just used
  num_queries_made = len(session_state.graph_data_to_be_used)

  # Check if the model used the graph
  if num_queries_made > 0:
    extracted_data = session_state.extracted_data[-1]
    
    # Display the results from the knowledge graph
    for i in range(-1, -num_queries_made - 1, -1): # backward loop
      cypher_code = session_state.graph_data_to_be_used[i]
      output = session_state.good_cypher_and_outputs[cypher_code]
      output = ast.literal_eval(output)

      if len(output) > 0:
        st.markdown(f"""
                  <h1 style="font-size: 25px; text-align: center; background-color: #F0F2F6; border-radius:5px; padding: 10px; margin-bottom: 20px">
                    Knowledge Graph of Agent's Query {abs(i)}
                  </h1>""",  unsafe_allow_html=True)
        
        # Display Knowledge Graph
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

      # If output is empty
      else:
        display_error_box(text="⚠️ Agent used the graph but the output is empty ⚠️")
    
    # Display Extracted Data Graph
    try:
      st.markdown(f"""
              <h1 style="font-size: 25px; text-align: center; background-color: #F0F2F6; border-radius:5px; padding: 10px; margin-bottom: 20px">
                Agent's Extracted Data From Knowledge Graph
              </h1>""",  unsafe_allow_html=True)
      
      graph = display_extracted_traits_data(ast.literal_eval(extracted_data))
      st.plotly_chart(graph)
    except Exception as e:
      display_error_box(text="⚠️ Attempted to draw the graph, but the Agent returned an unexpected format. ⚠️")
  
  # If Agent didn't use the graph
  else:
    st.markdown(
      """
      <div style="font-size: 20px; margin-top: 20px; display: flex; justify-content: center; align-items: center; height: 100px;">
          <div style="text-align: center; background-color: #F0F2F6; border-radius: 10px; padding: 30px;">
              The <strong>Agent</strong> didn't use any data from the knowledge graph.<br>
              When the knowledge graph is used you will see the results here🙂<br><br>
              <strong>Note: </strong>The agent calls the knowledge graph when it decides to suggest career paths. So, make sure you finish the personality test🙃
          </div>
      </div>
      """, unsafe_allow_html=True
      )
  
  return session_state