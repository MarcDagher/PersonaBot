import ast
import streamlit as st
from sidebar import side_bar
from chat_page import display_chat_page
from knowledge_graph_page import display_knowledge_graph_page
from app_helper_functions import create_plotly_graph

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

#######################
# UI Order of Display #
#######################

# Side Bar (Page Navigator)
st.session_state = side_bar(session_state=st.session_state)

# Chat Page
if st.session_state.current_page == 'chat':
  new_session_state = display_chat_page(session_state=st.session_state)
  st.session_state = new_session_state

# Graph Page
elif st.session_state.current_page == 'graph':
  new_session_state = display_knowledge_graph_page(session_state=st.session_state)
  st.session_state = new_session_state