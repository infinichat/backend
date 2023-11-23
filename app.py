import time
from flask import Flask, make_response, request, render_template, jsonify
from flask_cors import CORS  # Import the CORS extension
import os
import requests
from dotenv import load_dotenv
import re
import mysql
import mysql.connector

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


load_dotenv()

#configure the database
db_config = {
        'host': '127.0.0.1',
        'user': 'root',
        'password': 'rootler90lop5__',
        'database': 'openai_test',
}

#Starting a thread Step 0
def start_thread_openai():
    token = os.getenv("api_key")
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

#Sending a message to a thread. Step 1
def send_message_user(thread_openai_id, json_payload):
    token = os.getenv("api_key")

    try:
        if thread_openai_id and json_payload:
            api_url = f"https://api.openai.com/v1/threads/{thread_openai_id}/messages"
            api_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "OpenAI-Beta": "assistants=v1",
                "User-Agent": "PostmanRuntime/7.34.0"
            }
            api_json_payload = {
                "role": "user",
                "content": json_payload.get("question", "")
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
    token = os.getenv("api_key")
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

def create_run(thread_openai_id):
    token = os.getenv("api_key")
    api_url = f"https://api.openai.com/v1/threads/{thread_openai_id}/runs"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "OpenAI-Beta": "assistants=v1",
        "User-Agent": "PostmanRuntime/7.34.0"
    }
    assistant_id = os.getenv("assistant_id")
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
    token = os.getenv("api_key")
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
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        query = "SELECT answer FROM chat_cache WHERE question REGEXP %s"
        cursor.execute(query, (question,))
        result = cursor.fetchone()

        print("querying db")

        if result:
            return result[0]
        else:
            return None

    except Exception as e:
        print(f"Error querying MySQL database: {e}")
        return None

    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def cache_response_in_database(question, answer):
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        query = "INSERT INTO chat_cache (question, answer) VALUES (%s, %s)"
        cursor.execute(query, (question, answer))

        print("inserting qa")

        connection.commit()

    except Exception as e:
        print(f"Error caching response in MySQL database: {e}")

    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


# execute flow
def execute_flow(payload):
    try:
        question = payload.get("question")
        if not question:
            raise ValueError("Invalid payload: 'question' is required.")

        # Check the MySQL database first
        cached_response = query_with_caching(question)

        if cached_response:
            # If the question is in the database, return the cached response
            return jsonify({"response": cached_response})
        else:
            # If the question is not in the database, continue with OpenAI flow
            thread_openai_id = start_thread_openai()
            send_message_user(thread_openai_id, json_payload={"question": question})
            ai_response = retrieve_ai_response(thread_openai_id)

            # Cache the response in the MySQL database for future use
            # Assuming there's a table named 'qa_table' with columns 'question' and 'answer'
            if ai_response:
                cache_response_in_database(question, ai_response)

            return jsonify({"response": ai_response})

    except Exception as e:
        print(f"Error executing flow: {e}")
        return jsonify({"error": f"Internal Server Error: {e}"}), 500

# # Function to cache the response in the MySQL database
# def cache_response_in_database(question, answer):
#     try:
#         connection = mysql.connector.connect(**db_config)
#         cursor = connection.cursor()

#         query = "INSERT INTO qa_table (question, answer) VALUES (%s, %s)"
#         cursor.execute(query, (question, answer))

#         connection.commit()

#     except Exception as e:
#         print(f"Error caching response in MySQL database: {e}")

#     finally:
#         if connection.is_connected():
#             cursor.close()
#             connection.close()

#HOME route
@app.route('/', methods=['GET', 'POST'])
def handle_api_requests():
    if request.method == 'POST':
        try:
            data = request.get_json()
            response = execute_flow(data)
            return response

        except Exception as e:
            print(f"Error executing flow: {e}")
            return jsonify({"error": "Internal Server Error"}), 500

    # Handle GET requests (if required)
    elif request.method == 'GET':
        # Perform actions for GET requests (if needed)
        return jsonify({"message": "This is a GET request"}), 200

if __name__ == "__main__":
    app.run(debug=True)

