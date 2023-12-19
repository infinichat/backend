import os
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import time
import psycopg2
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
import re

load_dotenv()

current_session_id = 'session_9dccadb3-3904-4685-8bbe-865adac80a37'


def check_conversation():
    website_id = os.getenv("website_id")
    username = os.getenv("crisp_identifier")
    password = os.getenv("crisp_key")
    basic_auth_credentials = (username, password)
    api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation/session_0f6517f5-1c74-414a-90ca-7431ca18aca7/messages"
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
        print(data)
        # if "data" in data and len(data["data"]) == 0 and data["data"][0]["from"] == "user":
        user_content_after_name = None
        found_name_question = False

        for item in data.get("data", []):
            print("Item:", item)

            if item.get("from") == "operator" and "What is your name?" in item.get("content", ""):
                found_name_question = True
            elif found_name_question and item.get("from") == "user":
                user_content_after_name = item["content"]
                print("User's message after 'What is your name?':", user_content_after_name)
                patch_profile(user_content_after_name, '098')
                break  # Assuming you want to process only the first message after the question
 # Assuming you want to process only the first message after the question

        #     user_content = data["data"][0]["content"]
        #     print("User's message:", user_content)
        # else:
        #     print("No valid message from the user found.")
        # if data is from user and this is only one message 
        # in the list 
        # then 
    except requests.exceptions.HTTPError as errh:
        print(f"HTTP Error: {errh}")
    except requests.exceptions.ConnectionError as errc:
        print(f"Error Connecting: {errc}")
    except requests.exceptions.Timeout as errt:
        print(f"Timeout Error: {errt}")
    except requests.exceptions.RequestException as err:
        print(f"Request Error: {err}")
    
if __name__ == "__main__":
    check_conversation()