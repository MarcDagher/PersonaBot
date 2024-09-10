import ast
import streamlit as st
from chat_page import display_chat_page
from app_helper_functions import create_plotly_graph

###########################
# General Initializations #
###########################

# Function to create a line that is used as a separator
def add_separator(color="#AAAAAA"):
  st.sidebar.markdown(
  f"""
    <div style="height: 1px; width: 100%; background-color: {color}"></div>
  """, unsafe_allow_html=True
  )

def set_current_page(page="chat"):
  st.session_state.current_page = page

#########################################
# Initialize Streamlit's Sesstion State #
#########################################
if not ("pages" and "current_page") in st.session_state:
  st.session_state.pages = ["chat", "graph"]
  st.session_state.current_page = "chat"

if "messages" not in st.session_state:
  st.session_state.messages = []

if not ("num_queries_made" and "cypher_code_and_query_outputs") in st.session_state:
  st.session_state.num_queries_made = 0
  st.session_state.cypher_code_and_query_outputs = []

###########
# Sidebar #
###########
st.sidebar.markdown("""
                    <strong style="font-size: 18px;">PersonaBot</strong> <span style="font-size: 15px;">is an agentic AI system designed to understand your personality then suggest career paths, with access to a Neo4j knowledge graph.</span>
                    """, unsafe_allow_html=True)

add_separator()

st.sidebar.button(label="Chat", on_click=set_current_page, kwargs={'page': 'chat'})
st.sidebar.button(label="Knowledge Graph", on_click=set_current_page, kwargs={'page': 'graph'})


if st.session_state.current_page == 'chat':
  new_session_state = display_chat_page(session_state=st.session_state)
  st.session_state = new_session_state

#######################
# Display Graph in UI #
#######################
elif st.session_state.current_page == 'graph':
  if st.session_state.num_queries_made > 0:
    output = st.session_state.cypher_code_and_query_outputs[-1]['output']
    if output:
      st.sidebar.write("We have a graph")
      graph = create_plotly_graph(ast.literal_eval(output))
      
      st.sidebar.plotly_chart(graph)
  else:
    st.sidebar.write("Ain't no graph yet")