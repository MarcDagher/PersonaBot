import streamlit as st
import requests

###########################
# General Initializations #
###########################

# Function to send a request to the FastAPI backend
def get_api_response(user_message):
    response = requests.post(url="http://127.0.0.1:8000/messages", json={"message": user_message})
    return response.json()

# Function to create a line that is used as a separator
def add_separator(color="#AAAAAA"):
  st.sidebar.markdown(
  f"""
    <div style="height: 1px; width: 100%; background-color: {color}"></div>
  """, unsafe_allow_html=True
  )

###############################
# Landing Page's Greeting Box #
###############################
if "messages" not in st.session_state:
  st.session_state.messages = []
  # grey: #F0F2F6
  # red: #FF4B4B
  st.markdown(
    """
    <div style="font-size: 20px; margin-top: 20px; display: flex; justify-content: center; align-items: center; height: 100px;">
        <div style="text-align: center; background-color: #F0F2F6; border-radius: 10px; padding: 30px;">
            Hello, I am <strong>PersonaBot</strong>.<br>
            Please let me know when you're ready 😊.
        </div>
    </div>
    """, unsafe_allow_html=True
    )

###########
# Sidebar #
###########
st.sidebar.markdown("""
                    <strong style="font-size: 18px;">PersonaBot</strong> <span style="font-size: 15px;">is an agentic AI system designed to understand your personality then suggest career paths, with access to a Neo4j knowledge graph.</span>
                    """, unsafe_allow_html=True)

add_separator()

############################
# Handle User Messages' UI #
############################
if prompt := st.chat_input(placeholder = "Your message ..."): # (:= assigns chat_input's result to prompt while checking if its none)
  # Add user message to chat history
  st.session_state.messages.append({"role": "user", "content": prompt})

##########################
# Handle AI Message's UI #
##########################
if prompt:
  # Receive AI's output
  api_output = get_api_response(user_message=prompt)
  
  # Check for errors
  if isinstance(api_output, str):
    st.session_state.messages.append({"role": "assistant", "content": f"Somthing went wrong: {api_output}."})

  # Save in messages and display it
  else:
    ai_response = api_output['response'][-1]
    st.session_state.messages.append({"role": "assistant", "content": ai_response})

##########################
# Display Messages in UI #
##########################
for message in st.session_state.messages:
  with st.chat_message(message["role"]):
    st.markdown(message["content"])