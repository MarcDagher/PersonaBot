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
  st.sidebar.image("Streamlit_Sub_Folder\Assets\PersonaBot.png", output_format='PNG', use_column_width=True)
  st.sidebar.markdown(""" 
                      <p style="font-size: 15px;">
                        An agentic AI system designed to test and analyze your personality. With access to a Neo4j knowledge graph, the system will suggest career paths suitable for your character.
                      </p>
                      """, unsafe_allow_html=True)

  add_separator()

  st.sidebar.button(label="Chat", on_click=set_current_page, kwargs={'page': 'chat'}, use_container_width=True, type='primary')
  st.sidebar.button(label="Knowledge Graph", on_click=set_current_page, kwargs={'page': 'graph'}, use_container_width=True)

  return session_state