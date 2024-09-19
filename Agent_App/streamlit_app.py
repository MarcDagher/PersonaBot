import ast
import streamlit as st
from Streamlit_Sub_Folder.Pages.sidebar import side_bar
from Streamlit_Sub_Folder.Pages.chat_page import display_chat_page
from Streamlit_Sub_Folder.Pages.knowledge_graph_page import display_knowledge_graph_page

#########################################
# Initialize Streamlit's Sesstion State #
#########################################
if not ("pages" and "current_page") in st.session_state:
  st.session_state.pages = ["chat", "graph"]
  st.session_state.current_page = "chat"

if "messages" not in st.session_state:
  st.session_state.messages = []

if not ("graph_data_to_be_used") in st.session_state:
  st.session_state.graph_data_to_be_used = []

if not "extracted_data" in st.session_state:
  st.session_state.extracted_data = []

#######################
# UI Order of Display #
#######################

# Side Bar (Page Navigator)
st.session_state = side_bar(session_state=st.session_state)

# Chat Page
if st.session_state.current_page == 'chat':
  st.session_state = display_chat_page(session_state=st.session_state)

# Graph Page
elif st.session_state.current_page == 'graph':
  st.session_state = display_knowledge_graph_page(session_state=st.session_state)