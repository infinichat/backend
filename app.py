import os
import uuid
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import time
import psycopg2
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
import re
from flask_cors import CORS
import psycopg2
from psycopg2 import OperationalError

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins='*')

load_dotenv()

db_config = {
    'host': os.getenv('PGHOST'),
    'database': os.getenv('PGDATABASE'),
    'user': os.getenv('PGUSER'),
    'password': os.getenv('PGPASSWORD'),
}


website_id = os.getenv('website_id')
username = os.getenv('crisp_identifier')
password = os.getenv('crisp_key')


first_messages = []
user_session_mapping = {}
user_thread_mapping = {}


def start_thread_openai():
    global thread_openai_id
    api_url = "https://api.openai.com/v1/threads"
    response = requests.post(
        api_url,
        headers={
            "OpenAI-Beta": "assistants=v1",
            "User-Agent": "PostmanRuntime/7.34.0",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        },
        json={},
    )

    if response.status_code == 200:
        data = response.json()
        thread_openai_id = data.get("id")
        print("Thread started successfully! Thread id:", thread_openai_id)

        return thread_openai_id
    else:
        print("Error starting OpenAI thread:", response.status_code, response.text)
        return None
    
@socketio.on('connect')
def handle_connect():
    global question_answered
    global conversation_checked
    global first_messages

    user_id = str(uuid.uuid4())  # Generate a unique user ID
    join_room(user_id)
    print(f'User {user_id} connected')
    emit('user_id', {'response': user_id}) 
    print(f'Sent {user_id}')
    session_id = start_conversation_crisp()
    user_session_mapping[user_id] = session_id
    print(session_id)
    thread_openai_id = start_thread_openai()
    user_thread_mapping[user_id] = thread_openai_id
    print(thread_openai_id)

    # Reset state for the new user
    question_answered = False
    conversation_checked = 0
    first_messages = []

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')  

@socketio.on('message_from_client')
def handle_send_message(data):
    print(data)
    user_id = data.get('user_id')
    message = data.get('message')
    print(user_id)
    print(message)
    session_id = user_session_mapping.get(user_id)

    if session_id:
        execute_flow(message, user_id, session_id)
    
    # execute_flow(message, user_id)


def start_conversation_crisp():
    # global current_session_id

    # if current_session_id:
    #     return current_session_id

    basic_auth_credentials = (username, password)
    api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation"
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'PostmanRuntime/7.35.0',
        'X-Crisp-Tier': 'plugin'
    }

    response = requests.post(
        api_url,
        headers=headers,
        auth=HTTPBasicAuth(*basic_auth_credentials),
    )

    if response.status_code == 201:
        data = response.json()
        current_session_id = data['data']['session_id']
        print(current_session_id)
        return current_session_id
    else:
        print(f"Request failed with status code {response.status_code}.")
        print(response.text)


# #start conversation in crisp and return session_id
def send_user_message_crisp(question, session_id):
    # session_id = start_conversation_crisp()
    # website_id = os.getenv("website_id")
    api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation/{session_id}/message"
    # username = os.getenv("crisp_identifier")
    # password = os.getenv("crisp_key")
    basic_auth_credentials=(username, password)
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'PostmanRuntime/7.35.0',
        'X-Crisp-Tier': 'plugin'
    }
    payload = {
        "type": "text",
        "from": "user",
        "origin": "chat",
        "content": question
    }
    response = requests.post(
        api_url,
        headers=headers,
        auth=HTTPBasicAuth(*basic_auth_credentials),
        json=payload
    )

    if response.status_code == 202:
        print(response.json())
    else:
        print(f"Request failed with status code {response.status_code}.")
        print(response.text)


global_fingerprint = None

# Function to send agent message and return the fingerprint
def send_agent_message_crisp(response, session_id):
    global global_fingerprint
    # session_id = start_conversation_crisp()
    # website_id = os.getenv("website_id")
    api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation/{session_id}/message"
    # username = os.getenv("crisp_identifier")
    # password = os.getenv("crisp_key")
    alert = "http://127.0.0.1:5000/edit"
    basic_auth_credentials = (username, password)
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'PostmanRuntime/7.35.0',
        'X-Crisp-Tier': 'plugin'
    }

    payload = {
        "type": "text",
        "from": "operator",
        "origin": "chat",
        "content": response
    }
    response = requests.post(
        api_url,
        headers=headers,
        auth=HTTPBasicAuth(*basic_auth_credentials),
        json=payload
    )

    if response.status_code == 202:
        data = response.json()
        global_fingerprint = data['data']['fingerprint']
        print(global_fingerprint)
        return global_fingerprint
    else:
        print(f"Request failed with status code {response.status_code}.")
        print(response.text)


@app.route('/')
def index():
    return render_template("index.html")

# ?
    

# socketio.on_namespace(ChatNamespace('/chat/1'))
# socketio.on_namespace(ChatNamespace('/chat/2'))

# thread_openai_id = None
token = os.getenv('token')


# thread_openai_id = None


#Sending a message to a thread. Step 1
def send_message_user(thread_openai_id, question):
    # token = os.getenv("api_key")
    try:
        if thread_openai_id and question:
            api_url = f"https://api.openai.com/v1/threads/{thread_openai_id}/messages"
            api_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "OpenAI-Beta": "assistants=v1",
                "User-Agent": "PostmanRuntime/7.34.0"
            }
            
            # user_question = json_payload.get("question", "")

            api_json_payload = {
                "role": "user",
                "content": question
            }

            api_response = requests.post(api_url, headers=api_headers, json=api_json_payload)
            api_response.raise_for_status()

            if api_response.status_code == 200:
                api_data = api_response.json()
                print("Message sent successfully!", api_data)
                
                # Create a run after sending a message
                create_run(thread_openai_id)
                
                return api_data
            else:
                print("Error sending message:", api_response.status_code, api_response.text)
                return None

    except requests.exceptions.RequestException as e:
        print(f"API Request Error: {e}")
        return None
    
# Create a run Step2
def check_run_status(thread_openai_id, run_id):
    # token = os.getenv("api_key")
    api_url = f"https://api.openai.com/v1/threads/{thread_openai_id}/runs/{run_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "OpenAI-Beta": "assistants=v1",
        "User-Agent": "PostmanRuntime/7.34.0"
    }

    while True:
        response = requests.get(api_url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            status = data.get("status")

            if status == "completed":
                print("Run status is completed. Retrieving AI response.")
                break  # Exit the loop if the run is completed
            else:
                print(f"Run status is {status}. Waiting for completion.")
                time.sleep(5)  # Wait for 5 seconds before checking again
        else:
            print(f"Error checking run status: {response.status_code}, {response.text}")
            break  # Exit the loop if there's an error

assistant_id = os.getenv('assistant_id')

def create_run(thread_openai_id):
    # token = os.getenv("api_key")
    api_url = f"https://api.openai.com/v1/threads/{thread_openai_id}/runs"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "OpenAI-Beta": "assistants=v1",
        "User-Agent": "PostmanRuntime/7.34.0"
    }
    json_payload = {
        "assistant_id": assistant_id
    }

    response = requests.post(api_url, headers=headers, json=json_payload)
    response.raise_for_status()

    if response.status_code == 200:
        data = response.json()
        run_id = data.get('id')
        print("Run created successfully!", run_id)
        check_run_status(thread_openai_id, run_id)
    

def retrieve_ai_response(thread_openai_id):
    # token = os.getenv("api_key")
    api_url = f"https://api.openai.com/v1/threads/{thread_openai_id}/messages"

    try:
        response = requests.get(
            api_url,
            headers={
                "Authorization": f"Bearer {token}",
                "OpenAI-Beta": "assistants=v1",
                "User-Agent": "PostmanRuntime/7.34.0",
                "Accept": "*/*"
            },
        )
        response.raise_for_status()

        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', 'application/json')
            
            if 'application/json' in content_type:
                data = response.json()
                print("API Response:", data)  # Add this line to print the entire response
                if 'data' in data and data['data']:
                    ai_response = data['data'][0]['content'][0]['text']['value']
                    print("Retrieved response successfully!", ai_response)
                    return ai_response
                else:
                    print("No messages found in the response.")
                    return None
            else:
                print("Invalid Content-Type. Expected application/json, got:", content_type)
                return None
        else:
            print("Error retrieving AI response:", response.status_code, response.text)
            return None

    except requests.exceptions.RequestException as e:
        print(f"API Request Error: {e}")
        return None
    
def query_with_caching(question):
    connection = None
    try:
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()

        # Remove punctuation and perform case-insensitive matching using regular expression
        cleaned_question = re.sub(r'[^\w\s]', '', question)
        query = "SELECT answer FROM chat_cache WHERE question ~* %s"
        cursor.execute(query, (cleaned_question,))
        result = cursor.fetchone()

        print("querying db")

        if result:
            return result[0]
        else:
            return None

    except psycopg2.OperationalError as e:
        print(f"Error connecting to the database: {e}")

    finally:
        try:
            if connection:
                connection.close()
        except psycopg2.Error as e:
            print(f"Error closing the database connection: {e}")
        finally:
            if cursor:
                cursor.close()



# def query_with_caching(question):
#     connection = None
#     try:
#         connection = psycopg2.connect(**db_config)
#         cursor = connection.cursor()

#         # Remove punctuation and perform case-insensitive matching using regular expression
#         cleaned_question = re.sub(r'[^\w\s]', '', question)

#         # Update the regex pattern to include Ukrainian letters and use the re.UNICODE flag
#         query = "SELECT answer FROM chat_cache WHERE question ~* %s"
#         cursor.execute(query, (cleaned_question,), flags=re.UNICODE)
#         result = cursor.fetchone()

#         print("querying db")

#         if result:
#             return result[0]
#         else:
#             return None

#     except psycopg2.Error as e:
#         print(f"Error querying PostgreSQL database: {e}")
#         return None

#     finally:
#         if connection and connection.closed == 0:
#             cursor.close()
#             connection.close()


def cache_response_in_database(question, answer):
    connection = None
    try:
        connection = psycopg2.connect(**db_config)
        cursor = connection.cursor()

        query = "INSERT INTO chat_cache (question, answer) VALUES (%s, %s)"
        cursor.execute(query, (question, answer))

        print("inserting qa")

        connection.commit()

    except psycopg2.OperationalError as e:
        print(f"Error connecting to the database: {e}")

    finally:
        try:
            if cursor:
                cursor.close()
        except psycopg2.Error as e:
            print(f"Error closing the cursor: {e}")

        try:
            if connection:
                connection.close()
        except psycopg2.Error as e:
            print(f"Error closing the database connection: {e}")

first_question = 'What is your name?'
second_question = 'What is your phone number?'

# Modify patch_profile to accept nickname and phone_number as arguments
def patch_profile(nickname, phone_number, session_id):
    # website_id = os.getenv("website_id")
    # username = os.getenv("crisp_identifier")
    # password = os.getenv("crisp_key")
    basic_auth_credentials = (username, password)
    api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation/{session_id}/meta"
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'PostmanRuntime/7.35.0',
        'X-Crisp-Tier': 'plugin'
    }

    payload = {
        "nickname": nickname,
        "data": {
            "phone": phone_number
        }
    }

    try:
        response = requests.patch(
            api_url,
            headers=headers,
            auth=HTTPBasicAuth(*basic_auth_credentials),
            json=payload
        )

        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
        print(response.json())
   
    except requests.exceptions.HTTPError as errh:
        print(f"HTTP Error: {errh}")
    except requests.exceptions.ConnectionError as errc:
        print(f"Error Connecting: {errc}")
    except requests.exceptions.Timeout as errt:
        print(f"Timeout Error: {errt}")
    except requests.exceptions.RequestException as err:
        print(f"Request Error: {err}")


def check_conversation(session_id):
    # website_id = os.getenv("website_id")
    # username = os.getenv("crisp_identifier")
    # password = os.getenv("crisp_key")
    basic_auth_credentials = (username, password)
    api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation/{session_id}/messages"
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'PostmanRuntime/7.35.0',
        'X-Crisp-Tier': 'plugin'
    }
    try:
        response = requests.get(
            api_url,
            headers=headers,
            auth=HTTPBasicAuth(*basic_auth_credentials),
        )

        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
        data = response.json()

        user_content_after_name = None
        user_content_after_number = None
        found_name_question = False
        found_number_question = False

        for item in data.get("data", [0]):
            print("Item:", item)
            if item.get("from") == "operator" and "Як до вас звертатись?" in item.get("content", ""):
                found_name_question = True
            elif found_name_question and item.get("from") == "user":
                user_content_after_name = item["content"]
                print("User's message after 'What is your name?':", user_content_after_name)
                break
        
        for item in data.get("data", [1]):
            print("Item:", item)
            if item.get("from") == "operator" and "Вкажіть будь ласка свій номер телефону для подальшого зв'язку з Вами." in item.get("content", ""):
                found_number_question = True
            elif found_number_question and item.get("from") == "user":
                user_content_after_number = item["content"]
                print("User's message after 'What is your phone number?':", user_content_after_number)
                break

        print("Patching profile: " + str(user_content_after_name) + ", " + str(user_content_after_number))
        patch_profile(user_content_after_name, user_content_after_number, session_id)
            
    except requests.exceptions.HTTPError as errh:
        print(f"HTTP Error: {errh}")
    except requests.exceptions.ConnectionError as errc:
        print(f"Error Connecting: {errc}")
    except requests.exceptions.Timeout as errt:
        print(f"Timeout Error: {errt}")
    except requests.exceptions.RequestException as err:
        print(f"Request Error: {err}")

first_messages = [] 

conversation_checked = 0
question_answered = False

def execute_flow(message, user_id, session_id):
    # thread_openai_id = user_thread_mapping.get(user_id)
    global current_session_id
    global question_answered
    global conversation_checked
    global first_messages

    question = message

    if not question:
        raise ValueError("Invalid payload: 'question' is required.")

    send_user_message_crisp(question, session_id)
    try: 
        if not question_answered and conversation_checked == 0:
            print('Appending the first question')
            first_messages.append(question)
            cached_response = query_with_caching(first_messages[0])
            print("Executing check_conversation() for the first time")
            send_agent_message_crisp('Як до вас звертатись?', session_id)
            # send_await_message('Як до вас звертатись?')
            emit('start', {'user_id': user_id, 'message': 'Як до вас звертатись?'}, room=user_id)
            # check_conversation()
            conversation_checked += 1
        elif not question_answered and conversation_checked == 1:
            print("Executing check_conversation() for the second time")

            emit('start', {'user_id': user_id, 'message': "Вкажіть будь ласка свій номер телефону для подальшого зв'язку з Вами."}, room=user_id)
            send_agent_message_crisp("Вкажіть будь ласка свій номер телефону для подальшого зв'язку з Вами.", session_id)
            # check_conversation()
            conversation_checked += 1

        elif not question_answered and conversation_checked == 2:
            cached_response = query_with_caching(first_messages[0])
            check_conversation(session_id)
            if cached_response:
                    # If the question is in the database, return the cached response
                    # Assuming you have defined send_agent_message_crisp somewhere in your code
                emit('start', {'user_id': user_id, 'message': cached_response}, room=user_id)
                send_agent_message_crisp(cached_response, session_id)
               
            else:
                print('Going into the condition')
                thread_openai_id = user_thread_mapping.get(user_id)

                emit('start', {'user_id': user_id, 'message': 'Ваш запит в обробці. Це може зайняти до 1 хвилини'}, room=user_id)
                    # Assuming you have defined send_message_user somewhere in your code
                send_message_user(thread_openai_id, first_messages[0])
                # emit('start', {'user_id': user_id, 'message': 'Ваш запит в обробці. Це може зайняти до 1 хвилини'}, room=user_id)

                    # Retrieve AI response
                    # Assuming you have defined retrieve_ai_response somewhere in your code

                ai_response = retrieve_ai_response(thread_openai_id)

                    # Cache the response in the MySQL database for future use
                    # Assuming you have defined cache_response_in_database somewhere in your code
                if ai_response:
                    # send_await_message()
                    send_agent_message_crisp(ai_response, session_id)
                    emit('start', {'user_id': user_id, 'message': ai_response}, room=user_id)
                    cache_response_in_database(first_messages[0], ai_response)

            conversation_checked += 1
        else:
            print("Skipped check_conversation()")
            # send_await_message()

            # Assuming you have defined query_with_caching somewhere in your code
            cached_response = query_with_caching(question)

            if cached_response:
                    # If the question is in the database, return the cached response
                    # Assuming you have defined send_agent_message_crisp somewhere in your code
                emit('start', {'user_id': user_id, 'message': cached_response}, room=user_id)
                send_agent_message_crisp(cached_response, session_id)
               

            else:
                thread_openai_id = user_thread_mapping.get(user_id)

                    # Assuming you have defined send_message_user somewhere in your code
                emit('start', {'user_id': user_id, 'message': 'Ваш запит в обробці. Це може зайняти до 1 хвилини'}, room=user_id)

                send_message_user(thread_openai_id, question)
                
                # emit('start', {'user_id': user_id, 'message': 'Ваш запит в обробці. Це може зайняти до 1 хвилини'}, room=user_id)

                    # Retrieve AI response
                    # Assuming you have defined retrieve_ai_response somewhere in your code
                ai_response = retrieve_ai_response(thread_openai_id)

                    # Cache the response in the MySQL database for future use
                    # Assuming you have defined cache_response_in_database somewhere in your code
                if ai_response:
                    emit('start', {'user_id': user_id, 'message': ai_response}, room=user_id)
                    send_agent_message_crisp(ai_response, session_id)
                    cache_response_in_database(question, ai_response)
            
    # Check if the current question is a profile-related question
    except Exception as e:
        print(f"Error: {str(e)}")
        emit('start', {'user_id': user_id, 'message': 'Щось пішло не так, спробуйте пізніше...'}, room=user_id)