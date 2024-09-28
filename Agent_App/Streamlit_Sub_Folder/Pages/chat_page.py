import streamlit as st
from Streamlit_Sub_Folder.Helpers.api_functions import get_api_response

## Handles Conversational UI 
def display_chat_page(session_state):

  # Add user's message to sessions_state
  if prompt := st.chat_input(placeholder = "Your message ..."):
    session_state.messages.append({"role": "user", "content": prompt})

  # Send user's message to the Agent, recieve Agent's response, and save the response in sessions_state
  if prompt:
    api_output = get_api_response(user_message=prompt) # api_output: {response, num_queries_made, cypher_code_and_query_outputs}

    # Check for returned errors
    if isinstance(api_output, str):
      session_state.messages.append({"role": "assistant", "content": f"Somthing went wrong ({api_output})."})

    # Save response in session_state: messages, num_queries_made, cypher_code_and_query_outputs
    else:
      ai_response = api_output['response'][-1]
      session_state.messages.append({"role": "assistant", "content": f"{ai_response}"})
      
      session_state.extracted_data = api_output['extracted_data']
      session_state.good_cypher_and_outputs = api_output['good_cypher_and_outputs']
      session_state.graph_data_to_be_used = api_output['graph_data_to_be_used']


  # Display Conversation in the UI
  for message in session_state.messages:
    with st.chat_message(message["role"]):
      st.markdown(message["content"])

  # Displays greeting UI if conversation is empty
  if len(session_state.messages) == 0:
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
    
  # Return adjust session_state in order to update it in the app
  return session_state