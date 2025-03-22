import os
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from openai import OpenAI
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

app = Flask(__name__)
CORS(app)

# Message limit tracking
RESET_INTERVAL = timedelta(hours=24)
user_messages = defaultdict(lambda: {'count': 0, 'last_reset': datetime.now()})

def check_and_update_message_limit(user_id):
    try:
        # Get user data from Firebase
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return False, "User not found"
            
        user_data = user_doc.to_dict()
        current_time = datetime.now()
        
        # Check if user is suspended
        if user_data.get('suspended', False):
            return False, "Your account is suspended"
            
        # Get daily limit (null/None means unlimited)
        daily_limit = user_data.get('dailyLimit')
        if daily_limit is None:
            return True, "No message limit (Unlimited)"
            
        # Get last reset time
        last_reset = user_data.get('lastResetTime', current_time).timestamp()
        last_reset_dt = datetime.fromtimestamp(last_reset)
        
        # Reset count if 24 hours have passed
        if current_time - last_reset_dt >= RESET_INTERVAL:
            user_ref.update({
                'messageCount': 1,  # First message of new period
                'lastResetTime': current_time
            })
            message_count = 1
        else:
            message_count = user_data.get('messageCount', 0) + 1
            
        # Check if user has exceeded their limit
        if message_count > daily_limit:
            time_until_reset = last_reset_dt + RESET_INTERVAL - current_time
            hours, remainder = divmod(int(time_until_reset.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
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
        return False, "Error checking message limit"

# Get API key
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("ERROR: OpenAI API key not found in .env file")
    exit(1)

# Initialize OpenAI client
try:
    client = OpenAI(api_key=api_key)
except Exception as e:
    print(f"ERROR initializing OpenAI client: {str(e)}")
    exit(1)

@app.route("/", methods=['GET'])
def home():
    return send_from_directory('.', 'index.html')

@app.route("/ai", methods=['GET'])
def ai_page():
    return send_from_directory('.', 'AI.html')

@app.route("/<path:filename>")
def serve_file(filename):
    return send_from_directory('.', filename)

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

        # Get AI response
        try:
            print("Sending request to OpenAI")
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ]
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
        # Get user data from Firebase
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return jsonify({"error": "User not found"}), 404
            
        user_data = user_doc.to_dict()
        current_time = datetime.now()
        
        # Get daily limit
        daily_limit = user_data.get('dailyLimit')
        if daily_limit is None:
            return jsonify({
                "message": "No message limit (Unlimited)",
                "hours_until_reset": 0,
                "minutes_until_reset": 0
            })
            
        # Get last reset time and message count
        last_reset = user_data.get('lastResetTime', current_time).timestamp()
        last_reset_dt = datetime.fromtimestamp(last_reset)
        message_count = user_data.get('messageCount', 0)
        
        # Reset count if 24 hours have passed
        if current_time - last_reset_dt >= RESET_INTERVAL:
            message_count = 0
            user_ref.update({
                'messageCount': 0,
                'lastResetTime': current_time
            })
            
        # Calculate remaining messages
        remaining_messages = daily_limit - message_count
        
        # Calculate time until reset
        time_until_reset = last_reset_dt + RESET_INTERVAL - current_time
        hours, remainder = divmod(int(time_until_reset.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        
        return jsonify({
            "message": f"Messages remaining today: {remaining_messages} | Resets in {hours}h {minutes}m",
            "hours_until_reset": hours,
            "minutes_until_reset": minutes
        })
        
    except Exception as e:
        print(f"Error getting remaining messages: {str(e)}")
        return jsonify({"error": "Error getting remaining messages"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=8000)