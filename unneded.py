# Start a background thread to send messages continuously
# message_thread = threading.Thread(target=check_the_last_message)

# # Start the thread
# message_thread.start()

# message_data = {}

# @socketio.on('send_message')
# def send_message(message, fingerprint):
#     print(f"Message received: {message}" + f"Fingerprint received: {fingerprint}")
#     socketio.emit('start', {'response': message})
#     message_data[fingerprint] = message
    
    
# @socketio.on('message_to_delete')
# def delete_message(fingerprint):
#     # Check if the fingerprint exists in the message_data dictionary
#     if fingerprint in message_data:
#         # If it exists, retrieve the corresponding message
#         del_message = message_data[fingerprint]

#         print(f"Message to delete: {del_message}")
        
#         # Emit an event to notify the client or perform any other actions
#         socketio.emit('delete_message', {'response': del_message})
#     else:
#         print(f"No message found for fingerprint: {fingerprint}")

# @socketio.on('edit_message')
# def edit_message(new_message, fingerprint):
#     if fingerprint in message_data:
#         # Retrieve the existing message
#         old_message = message_data[fingerprint]
#         socketio.emit('delete_message', {'response': old_message})

#         # Update the message in the dictionary
#         message_data[fingerprint] = new_message

#         print(f"Message edited. Old message: {old_message}, New message: {new_message}")

#         # Emit an event to notify the client or perform any other actions
#         socketio.emit('start', {'response': new_message})
#     else:
#         print(f"No message found for fingerprint: {fingerprint}")


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


# Start a background thread to send messages continuously
# message_thread = threading.Thread(target=check_the_last_message)

# # Start the thread
# message_thread.start()

# message_data = {}

# @socketio.on('send_message')
# def send_message(message, fingerprint):
#     print(f"Message received: {message}" + f"Fingerprint received: {fingerprint}")
#     socketio.emit('start', {'response': message})
#     message_data[fingerprint] = message
    
    
# @socketio.on('message_to_delete')
# def delete_message(fingerprint):
#     # Check if the fingerprint exists in the message_data dictionary
#     if fingerprint in message_data:
#         # If it exists, retrieve the corresponding message
#         del_message = message_data[fingerprint]

#         print(f"Message to delete: {del_message}")
        
#         # Emit an event to notify the client or perform any other actions
#         socketio.emit('delete_message', {'response': del_message})
#     else:
#         print(f"No message found for fingerprint: {fingerprint}")

# @socketio.on('edit_message')
# def edit_message(new_message, fingerprint):
#     if fingerprint in message_data:
#         # Retrieve the existing message
#         old_message = message_data[fingerprint]
#         socketio.emit('delete_message', {'response': old_message})

#         # Update the message in the dictionary
#         message_data[fingerprint] = new_message

#         print(f"Message edited. Old message: {old_message}, New message: {new_message}")

#         # Emit an event to notify the client or perform any other actions
#         socketio.emit('start', {'response': new_message})
#     else:
#         print(f"No message found for fingerprint: {fingerprint}")


# @socketio.on('message_from_client')
# def handle_message(message):
#     print('Received message:', message)

#     execute_flow(message, namespace)


from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    user_id = str(uuid.uuid4())  # Generate a unique user ID
    join_room(user_id)
    print(f'User {user_id} connected')
    emit('user_id', {'user_id': user_id})  # Send the user ID to the connected user

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('send_message')
def handle_send_message(data):
    user_id = data['user_id']
    message = data['message']
    emit('receive_message', {'user_id': user_id, 'message': message}, room=user_id)


if __name__ == '__main__':
    socketio.run(app, debug=True)
