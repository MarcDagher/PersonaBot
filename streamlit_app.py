import streamlit as st
import requests

# Function to send a request to the FastAPI backend
def get_api_response(user_message):
    response = requests.post(url="http://127.0.0.1:8000/query", json={"query": user_message})
    return response.json()

# Initialize chat history
if "messages" not in st.session_state:
  st.session_state.messages = []

# When the chat has no previous messages, don't load text boxes. Load a text instead
if len(st.session_state.messages) == 0:
  st.write("Testing")

else:
  # Display chat messages from history on app rerun
  for message in st.session_state.messages:
    with st.chat_message(message["role"]):
      st.markdown(message["content"])

## Handle User Messages (:= assigns chat_input's result to prompt while checking if its none)
if prompt := st.chat_input(placeholder = "Your message ..."):
  # Add user message to chat history
  st.session_state.messages.append({"role": "user", "content": prompt})
  # Render and display user message in chat message container
  with st.chat_message("user"):
    st.markdown(prompt)

if prompt:
  ## Handle AI response
  api_output = get_api_response(user_message=prompt)
  print("------------")
  print(len(api_output))
  print(api_output)
  print("------------")
  if isinstance(api_output, str):
    st.write(api_output)
  else:
    ai_response = api_output['response'][-1]
    with st.chat_message("assistant"):
      response = st.markdown(ai_response)
    st.session_state.messages.append({"role": "assistant", "content": ai_response})