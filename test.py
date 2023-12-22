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

current_session_id = 'session_7b1c461d-c87f-454d-bc64-d9e3553fc13b'


def check_conversation():
    website_id = os.getenv("website_id")
    username = os.getenv("crisp_identifier")
    password = os.getenv("crisp_key")
    basic_auth_credentials = (username, password)
    api_url = f"https://api.crisp.chat/v1/website/{website_id}/conversation/{current_session_id}/messages"
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

        for item in data.get("data", []):
            print("Item:", item)

            if item.get("from") == "operator" and "What is your name?" in item.get("content", ""):
                found_name_question = True
            elif found_name_question and item.get("from") == "user":
                user_content_after_name = item["content"]
                print("User's message after 'What is your name?':", user_content_after_name)
                break
        
        for item in data.get("data", [1]):
            print("Item:", item)
            if item.get("from") == "operator" and "What is your phone number?" in item.get("content", ""):
                found_number_question = True
            elif found_number_question and item.get("from") == "user":
                user_content_after_number = item["content"]
                print("User's message after 'What is your phone number?':", user_content_after_number)
                break
        
        print("Patching profile: " + str(user_content_after_name) + ", " + str(user_content_after_number))
        return user_content_after_name, user_content_after_number

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