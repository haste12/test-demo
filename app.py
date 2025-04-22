import os
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
import openai
from dotenv import load_dotenv
from prompt import SYSTEM_PROMPT, GREETING_RESPONSE, CREATOR_RESPONSE, PRESIDENT_RESPONSE, REPLACEMENTS
from datetime import datetime, timedelta
from collections import defaultdict
import firebase_admin
from firebase_admin import credentials, firestore

# Load environment variables from .env
load_dotenv()

# Initialize Firebase Admin
try:
    # For local development
    cred = credentials.Certificate("serviceAccountKey.json")
except:
    # For production (Railway)
    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": os.getenv("FIREBASE_PROJECT_ID"),
        "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
        "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "client_id": os.getenv("FIREBASE_CLIENT_ID"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL")
    })

firebase_admin.initialize_app(cred)
db = firestore.client()

app = Flask(__name__, static_folder='.')
CORS(app, resources={
    r"/*": {
        "origins": [
            "https://lfu-ai.my",
            "https://www.lfu-ai.my",
            "https://test-demo-production.up.railway.app",
            "https://login-form-96501.web.app",
            "http://localhost:5502",
            "http://localhost:5500",
            "http://localhost:5173",
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:5000",
            "http://127.0.0.1:5500",
            "http://127.0.0.1:5502",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:5000"
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Message limit tracking
RESET_INTERVAL = timedelta(hours=24)
user_messages = defaultdict(lambda: {'count': 0, 'last_reset': datetime.now()})
MAX_HISTORY_MESSAGES = 10  # Maximum number of previous messages to include

def check_and_update_message_limit(user_id):
    try:
        print(f"Checking message limit for user: {user_id}")
        # Get user data from Firebase
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            print(f"User not found: {user_id}")
            return False, "User not found"
            
        user_data = user_doc.to_dict()
        print(f"User data: {user_data}")
        current_time = datetime.now()
        
        # Check if user is suspended
        if user_data.get('suspended', False):
            print(f"User is suspended: {user_id}")
            return False, "Your account is suspended"
            
        # Get daily limit (null/None means unlimited)
        daily_limit = user_data.get('dailyLimit')
        print(f"Daily limit: {daily_limit}")
        if daily_limit is None:
            return True, "No message limit (Unlimited)"
            
        # Get last reset time
        last_reset = user_data.get('lastResetTime', current_time).timestamp()
        last_reset_dt = datetime.fromtimestamp(last_reset)
        print(f"Last reset: {last_reset_dt}, Current time: {current_time}")
        
        # Reset count if 24 hours have passed
        if current_time - last_reset_dt >= RESET_INTERVAL:
            print(f"Resetting message count for user: {user_id}")
            user_ref.update({
                'messageCount': 1,  # First message of new period
                'lastResetTime': current_time
            })
            message_count = 1
        else:
            message_count = user_data.get('messageCount', 0) + 1
            print(f"Incrementing message count to: {message_count}")
            
        # Check if user has exceeded their limit
        if message_count > daily_limit:
            time_until_reset = last_reset_dt + RESET_INTERVAL - current_time
            hours, remainder = divmod(int(time_until_reset.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            print(f"User {user_id} has exceeded limit. Reset in {hours}h {minutes}m")
            return False, f"Message limit reached. Your limit will reset in {hours}h {minutes}m"
            
        # Increment message count
        user_ref.update({
            'messageCount': message_count
        })
        
        # Calculate remaining messages
        remaining_messages = daily_limit - message_count
        
        # Calculate time until reset
        time_until_reset = last_reset_dt + RESET_INTERVAL - current_time
        hours, remainder = divmod(int(time_until_reset.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        
        return True, f"Messages remaining today: {remaining_messages} | Resets in {hours}h {minutes}m"
        
    except Exception as e:
        print(f"Error checking message limit: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Error args: {e.args}")
        import traceback
        print(traceback.format_exc())
        return False, "Error checking message limit"

# Get API key
print("Checking for OpenAI API key...")
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    # Remove any type of quotes and whitespace
    api_key = api_key.strip().strip('"').strip("'").strip('"').strip("'")
    print(f"API Key found: Yes")
    print(f"API Key length: {len(api_key)}")
    print(f"API Key starts with: {api_key[:4]}...")
    print(f"API Key value: {api_key}")  # This will help us debug
else:
    print("ERROR: OpenAI API key not found in environment variables")
    print("Available environment variables:", os.environ.keys())
    exit(1)

# Initialize OpenAI client
try:
    print("Initializing OpenAI client...")
    openai_client = openai.OpenAI(api_key=api_key)
    print("OpenAI client initialized successfully")
except Exception as e:
    print(f"ERROR initializing OpenAI client: {str(e)}")
    print(f"Error type: {type(e)}")
    print(f"Error args: {e.args}")
    print(f"API Key being used: {api_key}")  # This will help us debug
    exit(1)

@app.route("/", methods=['GET'])
def home():
    return send_from_directory('.', 'index.html')

@app.route("/AI.html", methods=['GET'])
def ai_page():
    return send_from_directory('.', 'AI.html')

@app.route("/<path:filename>")
def serve_file(filename):
    return send_from_directory('.', filename)

# Get chat history for a user from Firebase
def get_chat_history(user_id, limit=MAX_HISTORY_MESSAGES):
    try:
        print(f"Getting chat history for user: {user_id}, limit: {limit}")
        # Get chat history from Firebase
        chats_ref = db.collection('chats')
        query = chats_ref.where('userId', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
        
        chat_docs = query.get()
        
        # Convert to list and reverse to get chronological order
        chat_history = []
        for doc in chat_docs:
            chat_data = doc.to_dict()
            # Only add if both messages are present
            if 'userMessage' in chat_data and 'aiReply' in chat_data:
                chat_history.append({
                    'user': chat_data['userMessage'],
                    'ai': chat_data['aiReply'],
                    'timestamp': chat_data.get('timestamp', None)
                })
        
        # Reverse to get chronological order (oldest first)
        chat_history.reverse()
        print(f"Retrieved {len(chat_history)} history messages")
        return chat_history
    
    except Exception as e:
        print(f"Error getting chat history: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return []

@app.route("/chat", methods=['POST'])
def chat():
    try:
        print("Received chat request")
        print("Request headers:", request.headers)
        print("Request data:", request.get_data())
        
        if not request.is_json:
            print("Error: Request is not JSON")
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        print("Parsed JSON data:", data)
        
        if not data or 'message' not in data:
            print("Error: No message in data")
            return jsonify({"error": "No message provided"}), 400

        # Check for user ID
        user_id = data.get('userId')
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400

        # Check message limit
        can_send, limit_message = check_and_update_message_limit(user_id)
        if not can_send:
            return jsonify({"error": limit_message}), 429  # 429 Too Many Requests
        
        user_message = data['message'].strip()
        print(f"Processing message: {user_message}")

        # Handle simple greetings
        message_lower = user_message.lower()
        if message_lower in ["hello", "hi", "hey"]:
            return jsonify({
                "reply": GREETING_RESPONSE,
                "remaining_messages": limit_message
            })

        # Handle creator question
        if message_lower in ["who created you ?", "who is created you ? ", "who create you ?"]:
            return jsonify({
                "reply": CREATOR_RESPONSE,
                "remaining_messages": limit_message
            })

        # Handle known facts
        if "president of lebanese french university" in message_lower:
            return jsonify({
                "reply": PRESIDENT_RESPONSE,
                "remaining_messages": limit_message
            })

        # Get chat history
        chat_history = get_chat_history(user_id)
        
        # Prepare messages for OpenAI
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Add chat history
        for chat in chat_history:
            messages.append({"role": "user", "content": chat['user']})
            messages.append({"role": "assistant", "content": chat['ai']})
        
        # Add current message
        messages.append({"role": "user", "content": user_message})
        
        print(f"Sending {len(messages)} messages to OpenAI")

        # Get AI response
        try:
            print("Sending request to OpenAI")
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages
            )
            print("Received response from OpenAI")
            
            bot_reply = response.choices[0].message.content
            print("Bot reply:", bot_reply)
            
            # Clean up response using replacements from prompt.py
            for old_text, new_text in REPLACEMENTS.items():
                bot_reply = bot_reply.replace(old_text, new_text)

            return jsonify({
                "reply": bot_reply,
                "remaining_messages": limit_message
            })
            
        except Exception as api_error:
            print(f"AI API error: {str(api_error)}")
            return jsonify({"error": f"OpenAI API error: {str(api_error)}"}), 500

    except Exception as e:
        print(f"Server error: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/remaining_messages/<user_id>", methods=['GET'])
def get_remaining_messages(user_id):
    try:
        print(f"Getting remaining messages for user: {user_id}")
        # Get user data from Firebase
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            print(f"User not found: {user_id}")
            return jsonify({"error": "User not found"}), 404
            
        user_data = user_doc.to_dict()
        print(f"User data: {user_data}")
        current_time = datetime.now()
        
        # Get daily limit
        daily_limit = user_data.get('dailyLimit')
        print(f"Daily limit: {daily_limit}")
        if daily_limit is None:
            return jsonify({
                "message": "No message limit (Unlimited)",
                "hours_until_reset": 0,
                "minutes_until_reset": 0,
                "remaining_messages": -1  # Unlimited
            })
            
        # Get last reset time and message count
        last_reset = user_data.get('lastResetTime', current_time).timestamp()
        last_reset_dt = datetime.fromtimestamp(last_reset)
        message_count = user_data.get('messageCount', 0)
        print(f"Last reset: {last_reset_dt}, Current time: {current_time}, Message count: {message_count}")
        
        # Reset count if 24 hours have passed
        if current_time - last_reset_dt >= RESET_INTERVAL:
            print(f"Resetting message count for user: {user_id}")
            message_count = 0
            user_ref.update({
                'messageCount': 0,
                'lastResetTime': current_time
            })
            
        # Calculate remaining messages
        remaining_messages = daily_limit - message_count
        print(f"Remaining messages: {remaining_messages}")
        
        # Calculate time until reset
        time_until_reset = last_reset_dt + RESET_INTERVAL - current_time
        hours, remainder = divmod(int(time_until_reset.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        print(f"Time until reset: {hours}h {minutes}m")
        
        response_data = {
            "message": f"Messages remaining today: {remaining_messages} | Resets in {hours}h {minutes}m",
            "hours_until_reset": hours,
            "minutes_until_reset": minutes,
            "remaining_messages": remaining_messages
        }
        print(f"Response data: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error getting remaining messages: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Error args: {e.args}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": "Error getting remaining messages"}), 500

@app.route("/chat_history/<user_id>", methods=['GET'])
def get_chat_history_endpoint(user_id):
    try:
        print(f"Getting chat history for user: {user_id}")
        chat_history = get_chat_history(user_id, limit=50)  # Get more messages for the history endpoint
        
        # Format for the frontend
        formatted_history = []
        for chat in chat_history:
            formatted_history.append({
                "userMessage": chat['user'],
                "aiReply": chat['ai'],
                "timestamp": chat['timestamp'].timestamp() if chat['timestamp'] else None
            })
        
        return jsonify({
            "success": True,
            "history": formatted_history,
            "count": len(formatted_history)
        })
        
    except Exception as e:
        print(f"Error getting chat history: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": "Error getting chat history"}), 500

@app.route("/clear_chat_history/<user_id>", methods=['DELETE'])
def clear_chat_history(user_id):
    try:
        print(f"Clearing chat history for user: {user_id}")
        
        # Get chat documents from Firestore
        chats_ref = db.collection('chats')
        query = chats_ref.where('userId', '==', user_id)
        chat_docs = query.get()
        
        # Delete each document
        count = 0
        for doc in chat_docs:
            doc.reference.delete()
            count += 1
            
        print(f"Deleted {count} chat messages for user {user_id}")
        
        return jsonify({
            "success": True,
            "deleted_count": count,
            "message": f"Chat history cleared for user {user_id}"
        })
        
    except Exception as e:
        print(f"Error clearing chat history: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": "Error clearing chat history"
        }), 500

if __name__ == "__main__":
    # Get port from environment variable for Railway
    port = int(os.environ.get("PORT", 5000))
    # In production, host should be 0.0.0.0 for Railway
    host = '0.0.0.0' if os.environ.get("RAILWAY_ENVIRONMENT") else '127.0.0.1'
    app.run(debug=os.environ.get("DEBUG", "True").lower() == "true", 
           host=host, 
           port=port)