import streamlit as st

def set_current_page(page="chat"):
  st.session_state.current_page = page

# Function to create a line that is used as a separator
def add_separator(color="#AAAAAA"):
  st.sidebar.markdown(
  f"""
    <div style="height: 1px; width: 100%; background-color: {color}"></div>
  """, unsafe_allow_html=True
  )

def side_bar(session_state):

  st.sidebar.markdown("""
                      <strong style="font-size: 18px;">PersonaBot</strong> <span style="font-size: 15px;">is an agentic AI system designed to understand your personality then suggest career paths, with access to a Neo4j knowledge graph.</span>
                      """, unsafe_allow_html=True)

  add_separator()

  st.sidebar.button(label="Chat", on_click=set_current_page, kwargs={'page': 'chat'})
  st.sidebar.button(label="Knowledge Graph", on_click=set_current_page, kwargs={'page': 'graph'})

  return session_state