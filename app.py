import os
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
import openai
from dotenv import load_dotenv
from prompt import SYSTEM_PROMPT, GREETING_RESPONSE, CREATOR_RESPONSE, PRESIDENT_RESPONSE, REPLACEMENTS
from datetime import datetime, timedelta
from collections import defaultdict
from functools import lru_cache
import firebase_admin
from firebase_admin import credentials, firestore
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import json
from urllib.parse import quote_plus

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
   
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            print(f"User not found: {user_id}")
            return False, "User not found"
            
        user_data = user_doc.to_dict()
        print(f"User data: {user_data}")
        current_time = datetime.now()
        
        
        if user_data.get('suspended', False):
            print(f"User is suspended: {user_id}")
            return False, "Your account is suspended"
            
       
        daily_limit = user_data.get('dailyLimit')
        print(f"Daily limit: {daily_limit}")
        if daily_limit is None:
            return True, "No message limit (Unlimited)"
            
        
        last_reset = user_data.get('lastResetTime', current_time).timestamp()
        last_reset_dt = datetime.fromtimestamp(last_reset)
        print(f"Last reset: {last_reset_dt}, Current time: {current_time}")
        
       
        if current_time - last_reset_dt >= RESET_INTERVAL:
            print(f"Resetting message count for user: {user_id}")
            user_ref.update({
                'messageCount': 1,  
                'lastResetTime': current_time
            })
            message_count = 1
        else:
            message_count = user_data.get('messageCount', 0) + 1
            print(f"Incrementing message count to: {message_count}")
            
      
        if message_count > daily_limit:
            time_until_reset = last_reset_dt + RESET_INTERVAL - current_time
            hours, remainder = divmod(int(time_until_reset.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            print(f"User {user_id} has exceeded limit. Reset in {hours}h {minutes}m")
            return False, f"Message limit reached. Your limit will reset in {hours}h {minutes}m"
            
       
        user_ref.update({
            'messageCount': message_count
        })
        
       
        remaining_messages = daily_limit - message_count
        
     
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
    
    api_key = api_key.strip().strip('"').strip("'").strip('"').strip("'")
    print(f"API Key found: Yes")
    print(f"API Key length: {len(api_key)}")
    print(f"API Key starts with: {api_key[:4]}...")
    print(f"API Key value: {api_key}")  # This will help us debug
else:
    print("ERROR: OpenAI API key not found in environment variables")
    print("Available environment variables:", os.environ.keys())
    exit(1)


serp_api_key = os.getenv("SERP_API_KEY")
if serp_api_key:
    serp_api_key = serp_api_key.strip().strip('"').strip("'").strip('"').strip("'")
    print(f"SERP API Key found: Yes")
    print(f"SERP API Key length: {len(serp_api_key)}")
    print(f"SERP API Key starts with: {serp_api_key[:4]}...")
else:
    print("WARNING: SERP API key not found in environment variables. Web search functionality will be disabled.")

# NASA API key (https://api.nasa.gov) – allows fetching up-to-date space / astronomy data
NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY").strip()
if NASA_API_KEY == "DEMO_KEY":
    print("WARNING: Using NASA DEMO_KEY which is heavily rate-limited. Set NASA_API_KEY in environment for production.")
else:
    print("NASA API key loaded.")


try:
    print("Initializing OpenAI client...")
    openai_client = openai.OpenAI(api_key=api_key)
    print("OpenAI client initialized successfully")
except Exception as e:
    print(f"ERROR initializing OpenAI client: {str(e)}")
    print(f"Error type: {type(e)}")
    print(f"Error args: {e.args}")
    print(f"API Key being used: {api_key}")  
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

# Web search function using SERP API
def search_web(query):
    """
    Search the web using SERP API and return relevant information
    
    Args:
        query (str): The search query
        
    Returns:
        str: Formatted search results or error message
    """
    try:
        print(f"Searching the web for: {query}")
        
        if not serp_api_key:
            return "Web search is currently unavailable due to missing API key."
        
        # SERP API endpoint
        url = "https://serpapi.com/search"
        
        # Request parameters
        params = {
            "engine": "google",
            "q": query,
            "api_key": serp_api_key,
            "num": 5  # Limit to 5 results for conciseness
        }
        
       
        response = requests.get(url, params=params)
        
       
        if response.status_code == 200:
            data = response.json()
            
       
            organic_results = data.get("organic_results", [])
            
            if not organic_results:
                return "No relevant information found on the web for this query."
            
        
            formatted_results = "Here's what I found on the web:\n\n"
            
            for i, result in enumerate(organic_results, 1):
                title = result.get("title", "No title")
                link = result.get("link", "No link")
                snippet = result.get("snippet", "No description available")
                
                formatted_results += f"{i}. {title}\n"
                formatted_results += f"   {snippet}\n"
                formatted_results += f"   Source: {link}\n\n"
            
            return formatted_results
        else:
            print(f"SERP API error: {response.status_code}, {response.text}")
            return "Sorry, I couldn't search the web right now due to a technical issue."
            
    except Exception as e:
        print(f"Error in web search: {str(e)}")
        return "Sorry, I encountered an error while searching the web."

# ---------------- NASA INTEGRATION ---------------- #
##########################
# Dynamic Space Keyword Detection
##########################

# Core grouped keywords (semantic categories) — easy to extend in code
SPACE_KEYWORD_GROUPS = {
    "core": ["nasa", "space", "astronomy", "galaxy", "cosmos", "orbital", "spacecraft", "telescope"],
    "media": ["apod", "picture of the day", "astronomy picture", "space photo", "space image"],
    "mars": ["mars", "mars rover", "perseverance", "curiosity", "opportunity", "ingenuity"],
    "neo": ["neo", "asteroid", "asteroids", "near earth object", "meteor", "meteoroid"],
    "stations": ["iss", "iss position", "international space station"],
    "planets": ["planet positions", "planet alignment", "planets tonight"],
    "news": ["space news", "nasa news", "mission update", "launch schedule", "rocket launch"],
}

# Firestore path for custom keywords (document holds an array field 'keywords')
CUSTOM_KEYWORDS_DOC = ("config", "nasa_keywords")

@lru_cache(maxsize=1)
def _cached_custom_keywords(timestamp_bucket: int):
    """Internal cached fetch for custom keywords. timestamp_bucket groups calls per minute.
    Returns lower-cased list of custom keywords or empty list if missing.
    """
    try:
        col, doc = CUSTOM_KEYWORDS_DOC
        ref = db.collection(col).document(doc)
        snap = ref.get()
        if not snap.exists:
            return []
        data = snap.to_dict() or {}
        kws = data.get('keywords', [])
        if not isinstance(kws, list):
            return []
        return [str(k).lower() for k in kws]
    except Exception as e:
        print(f"Warning: could not load custom NASA keywords: {e}")
        return []

def get_all_space_keywords():
    """Aggregate all static + dynamic (Firestore) keywords into a flat list (lowercased)."""
    static = []
    for group_list in SPACE_KEYWORD_GROUPS.values():
        static.extend(group_list)
    # Bucket by minute for lightweight refresh (invalidate cache each minute)
    bucket = int(datetime.utcnow().timestamp() // 60)
    custom = _cached_custom_keywords(bucket)
    return list(dict.fromkeys([*static, *custom]))  # deduplicate preserving order

def is_nasa_query(message: str) -> bool:
    """Determine if message should trigger NASA data fetch.
    Logic:
      1. Direct keyword match (static or Firestore-added).
      2. Temporal Mars queries (e.g., "latest mars", "mars today").
    Add new keywords by either editing SPACE_KEYWORD_GROUPS or inserting into Firestore doc config/nasa_keywords.
    """
    msg = message.lower()
    keywords = get_all_space_keywords()
    if any(k for k in keywords if k in msg):
        return True
    # Temporal pattern for Mars-specific recency queries
    temporal = ["today", "latest", "current", str(datetime.now().year)]
    return ("mars" in msg) and any(t in msg for t in temporal)

def fetch_nasa_data(user_message: str) -> dict:
    """Fetch relevant NASA data based on the content of the user message.

    Returns a dict with keys: 'summary' (string for LLM context) and 'sources' (list of URLs)
    """
    results = {"summary": "", "sources": []}
    try:
        base_params = {"api_key": NASA_API_KEY}
        lower = user_message.lower()

        # Priority: APOD if asking for picture/photo of the day
        if any(p in lower for p in ["apod", "picture of the day", "astronomy picture", "space photo", "today's picture"]):
            apod_url = "https://api.nasa.gov/planetary/apod"
            r = requests.get(apod_url, params=base_params, timeout=10)
            if r.status_code == 200:
                data = r.json()  
                explanation = data.get("explanation", "")[:800]
                results["summary"] += f"Astronomy Picture of the Day (APOD) Title: {data.get('title')} Date: {data.get('date')} Explanation: {explanation} Media: {data.get('url')}\n"
                results["sources"].append(apod_url)

        # Mars rover photos if query mentions rover / mars
        if any(k in lower for k in ["mars", "rover", "perseverance", "curiosity", "opportunity"]):
            # Use Perseverance latest photos endpoint
            mars_url = "https://api.nasa.gov/mars-photos/api/v1/rovers/perseverance/latest_photos"
            r = requests.get(mars_url, params=base_params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                photos = data.get("latest_photos", [])[:3]
                if photos:
                    photo_summaries = []
                    for p in photos:
                        photo_summaries.append(
                            f"Camera {p.get('camera',{}).get('full_name')} on {p.get('earth_date')} -> {p.get('img_src')}"
                        )
                    results["summary"] += "Latest Perseverance Rover Photos (top 3): " + " | ".join(photo_summaries) + "\n"
                    results["sources"].append(mars_url)

        # Near-Earth Objects if asking about asteroid / NEO
        if any(k in lower for k in ["neo", "asteroid", "asteroids", "near earth object"]):
            neo_url = "https://api.nasa.gov/neo/rest/v1/feed"
            # Use today's date
            today = datetime.utcnow().strftime('%Y-%m-%d')
            params = {**base_params, "start_date": today, "end_date": today}
            r = requests.get(neo_url, params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                neos = data.get('near_earth_objects', {}).get(today, [])[:5]
                if neos:
                    neo_lines = []
                    for n in neos:
                        est = n.get('estimated_diameter', {}).get('meters', {})
                        diam = f"{est.get('estimated_diameter_min',0):.1f}-{est.get('estimated_diameter_max',0):.1f}m"
                        haz = 'Potentially Hazardous' if n.get('is_potentially_hazardous_asteroid') else 'Not Hazardous'
                        neo_lines.append(f"{n.get('name')} ({diam}, {haz})")
                    results["summary"] += "Today's Near-Earth Objects (sample): " + "; ".join(neo_lines) + "\n"
                    results["sources"].append(neo_url)

        if not results["summary"]:
            results["summary"] = "No specific NASA dataset matched, but user requested space/NASA info."
        return results
    except Exception as e:
        print(f"Error fetching NASA data: {e}")
        results["summary"] = "Encountered an error while fetching live NASA data."
        return results

def get_chat_history(user_id, limit=MAX_HISTORY_MESSAGES):
    try:
        print(f"Getting chat history for user: {user_id}, limit: {limit}")
        
        chats_ref = db.collection('chats')
        query = chats_ref.where('userId', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
        
        chat_docs = query.get()
        
        
        chat_history = []
        for doc in chat_docs:
            chat_data = doc.to_dict()
            
            if 'userMessage' in chat_data and 'aiReply' in chat_data:
                chat_history.append({
                    'user': chat_data['userMessage'],
                    'ai': chat_data['aiReply'],
                    'timestamp': chat_data.get('timestamp', None)
                })
        
      
        chat_history.reverse()
        print(f"Retrieved {len(chat_history)} history messages")
        return chat_history
    
    except Exception as e:
        print(f"Error getting chat history: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return []

def is_about_other_university(message):
    """Check if the message is about universities other than LFU."""
 
    message_lower = message.lower()
    
    other_university_keywords = [
        "university", "college", "campus", "academic", "faculty", "professor", 
        "student", "degree", "bachelor", "master", "phd", "major", "minor",
        "course", "class", "lecture", "semester", "education", "school"
    ]
    
    lfu_keywords = [
        "lebanese french university", "lfu", "lebanese-french", "lebanese french"
    ]
    
  
    has_university_terms = any(keyword in message_lower for keyword in other_university_keywords)
    about_lfu = any(keyword in message_lower for keyword in lfu_keywords)
    
 
    return has_university_terms and not about_lfu


def should_search_web(message, bot_reply):
    """
    Determine if we should search the web based on the message and AI's initial reply
    
    Args:
        message (str): User's message
        bot_reply (str): AI's initial reply
        
    Returns:
        bool: True if web search should be performed
    """
  
    message_lower = message.lower()
    reply_lower = bot_reply.lower()
    
  
    uncertainty_phrases = [
        "i don't know", "i do not know", "i'm not sure", "i am not sure", 
        "i don't have information", "i do not have information",
        "i don't have access", "i do not have access", 
        "i can't provide", "i cannot provide",
        "i don't have enough information", "i do not have enough information",
        "my knowledge is limited", "my information is limited",
        "my training data", "my training doesn't", "my training does not"
    ]
    

    

    is_uncertain = any(phrase in reply_lower for phrase in uncertainty_phrases)
 
    simple_greeting = message_lower in ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"]
    
 
    about_other_uni = is_about_other_university(message)
    

    return (is_uncertain or about_other_uni) and not simple_greeting

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
        
        print(f"Sending {len(messages)} base messages to OpenAI (pre NASA/web augmentation check)")

        # Optional NASA data injection BEFORE first model call to ground answer with fresh data
        nasa_context = None
        if is_nasa_query(user_message):
            print("Detected NASA-related query. Fetching NASA data...")
            nasa_data = fetch_nasa_data(user_message)
            nasa_context = f"Live NASA Data (fetched {datetime.utcnow().isoformat()}Z):\n{nasa_data['summary']}\nSources: " + ", ".join(set(nasa_data['sources']))
            messages.append({"role": "user", "content": "Use the following live NASA data while answering: " + nasa_context})
            print("NASA data appended to prompt.")

        # First AI response (already has NASA context if relevant)
        try:
            print("Sending initial request to OpenAI (with any NASA context)")
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages
            )
            bot_reply = response.choices[0].message.content
            print("Initial bot reply received.")

            # If uncertain or about other universities, perform web search augmentation
            if should_search_web(user_message, bot_reply):
                print("Uncertain / other university query. Performing web search augmentation...")
                web_results = search_web(user_message)
                messages.append({"role": "assistant", "content": bot_reply})
                messages.append({"role": "user", "content": "Incorporate these web search findings (cite sources): " + web_results})
                response = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages
                )
                bot_reply = response.choices[0].message.content
                print("Bot reply after web augmentation ready.")

            # If NASA context was used but not referenced, gently append a citation note
            if nasa_context and "nasa" not in bot_reply.lower():
                bot_reply += "\n\n(Answer informed by current NASA data.)"

            # Branding replacements
            for old_text, new_text in REPLACEMENTS.items():
                bot_reply = bot_reply.replace(old_text, new_text)

            # Persist conversation
            chat_ref = db.collection('chats').document()
            chat_ref.set({
                'userId': user_id,
                'userMessage': user_message,
                'aiReply': bot_reply,
                'timestamp': firestore.SERVER_TIMESTAMP
            })

            return jsonify({
                "reply": bot_reply,
                "remaining_messages": limit_message,
                "nasa_used": bool(nasa_context)
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

@app.route("/submit_feedback", methods=['POST'])
def submit_feedback():
    try:
        print("Received feedback submission")
        
        if not request.is_json:
            print("Error: Request is not JSON")
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        print("Parsed feedback data:", data)
        
        # Extract feedback data
        name = data.get('name', 'Anonymous')
        email = data.get('email', 'No email provided')
        message = data.get('message', '')
        user_id = data.get('userId', 'Not logged in')
        
        if not message:
            return jsonify({"error": "Feedback message is required"}), 400
            
        # Store feedback in Firestore
        feedback_ref = db.collection('feedback').document()
        feedback_ref.set({
            'name': name,
            'email': email,
            'message': message,
            'userId': user_id,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        
        # Send feedback via email
        try:
            # Email details - you would need to set up email credentials in environment variables
            receiver_email = "lfuai2025@gmail.com"
            subject = f"New Feedback from {name}"
            
            # Create email content
            email_content = f"""
            <html>
            <body>
                <h2>New Feedback Received</h2>
                <p><strong>From:</strong> {name}</p>
                <p><strong>Email:</strong> {email}</p>
                <p><strong>User ID:</strong> {user_id}</p>
                <p><strong>Message:</strong></p>
                <p>{message}</p>
                <p><em>Sent from LFU AI Feedback Form</em></p>
            </body>
            </html>
            """
            
            # For demonstration purposes, just log that we would send an email
            # In production, you would configure a proper email sending service
            print(f"Would send email to {receiver_email}:")
            print(f"Subject: {subject}")
            print(f"Content: {email_content}")
            
            # Note: To actually send emails, you would need to configure SMTP settings
            # Uncomment the following code and set up your email credentials in environment variables:
            # SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD
            
            smtp_server = os.getenv("SMTP_SERVER")
            smtp_port = int(os.getenv("SMTP_PORT", 587))
            smtp_username = os.getenv("SMTP_USERNAME")
            smtp_password = os.getenv("SMTP_PASSWORD")
            
            msg = MIMEMultipart()
            msg['From'] = smtp_username
            msg['To'] = receiver_email
            msg['Subject'] = subject
            msg.attach(MIMEText(email_content, 'html'))
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            return jsonify({
                "success": True,
                "message": "Feedback submitted successfully"
            })
            
        except Exception as email_error:
            print(f"Error sending feedback email: {str(email_error)}")
            # Still return success since we stored in Firestore
            return jsonify({
                "success": True,
                "message": "Feedback saved but email notification failed"
            })
        
    except Exception as e:
        print(f"Error submitting feedback: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": "Error submitting feedback"
        }), 500

if __name__ == "__main__":
    # Get port from environment variable for Railway
    port = int(os.environ.get("PORT", 5000))
    # In production, host should be 0.0.0.0 for Railway
    host = '0.0.0.0' if os.environ.get("RAILWAY_ENVIRONMENT") else '127.0.0.1'
    app.run(debug=os.environ.get("DEBUG", "True").lower() == "true", 
           host=host, 
           port=port)