# LFU AI Assistant

A Flask-based AI chatbot assistant for the Lebanese French University that uses OpenAI's GPT model to answer student queries about university information.

## Features

- Answers questions about university departments, faculty, services, and procedures
- Maintains chat history for users
- Enforces daily message limits based on user accounts
- Web search capability for unknown information using SERP API

## New Feature: Web Search Integration

The LFU AI Assistant now uses SERP API to search the web when it doesn't know the answer to a question. Instead of responding with "I don't know," the AI will:

1. Detect when it's uncertain about an answer
2. Use SERP API to search the web for relevant information
3. Generate a new, informed response based on the search results
4. Provide a helpful answer with the most up-to-date information

## Setup and Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up environment variables by copying `.env.example` to `.env` and filling in the values:

   ```
   cp .env.example .env
   ```

   Required environment variables:

   - `OPENAI_API_KEY`: Your OpenAI API key
   - `SERP_API_KEY`: Your SERP API key (get one at https://serpapi.com/users/sign_up)
   - Firebase configuration variables

4. Run the application:
   ```
   python app.py
   ```

## API Endpoints

- `/chat` (POST): Send a message to the AI and get a response
- `/remaining_messages/<user_id>` (GET): Check how many messages a user has left for the day
- `/chat_history/<user_id>` (GET): Get a user's chat history
- `/clear_chat_history/<user_id>` (DELETE): Clear a user's chat history

## Architecture

The application uses:

- Flask for the web server
- OpenAI API for AI responses
- SERP API for web search capability
- Firebase for user management and chat history storage
