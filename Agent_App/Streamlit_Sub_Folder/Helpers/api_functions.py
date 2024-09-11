import requests

# Function to send a request to the FastAPI backend
def get_api_response(user_message):
    response = requests.post(url="http://127.0.0.1:8000/messages", json={"message": user_message})
    return response.json()
