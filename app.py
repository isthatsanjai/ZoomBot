# app.py

import logging
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from config import Config
from rag_system import RAGSystem, initialize_rag_system, is_a_meaningful_message
from helper import JWT_generator
import db_manager  

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

rag_system = RAGSystem()

@app.after_request
def add_security_headers(response):
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    response.headers['Cross-Origin-Embedder-Policy'] = 'require-corp'
    response.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    if app.debug:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

@app.route('/')
def serve_bot_client():
    return render_template('index.html')

@app.route('/api/generate-sdk-signature', methods=['POST'])
def generate_sdk_signature():
    data = request.json
    meeting_number = data.get('meetingNumber')
    signature = JWT_generator(meeting_number)
    return jsonify({"signature": signature, "apiKey": Config.ZOOM_SDK_KEY})

@app.route('/api/process-chat', methods=['POST'])
def process_chat_message():
    data = request.json
    message = data.get('message', '')
    
    if not is_a_meaningful_message(message):
        return jsonify({"reply": None})

    # Get all necessary data from the frontend request
    is_host = data.get('is_host', False)
    is_cohost = data.get('is_cohost', False)
    is_privileged = is_host or is_cohost
    meeting_id = data.get('meeting_id')
    user_id = data.get('user_id')
    user_name = data.get('user_name')

    # Determine user role for logging
    if is_host:
        user_role = 'host'
    elif is_cohost:
        user_role = 'co-host'
    else:
        user_role = 'attendee'
    
    logger.info(f"Processing message: '{message}'")
    
    # Call the master method that contains all the logic
    response_data = rag_system.generate_response(message, is_privileged_user=is_privileged)
    
    # Log the full interaction to the PostgreSQL database
    bot_response_text = response_data.get('reply') or response_data.get('ack_message') or response_data.get('broadcast_message')
    bot_classification = response_data.get('bot_classification', 'Unknown')
    
    if meeting_id and user_id:
        db_manager.log_chat_interaction(
            meeting_id=meeting_id,
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            user_chat=message,
            chat_type='DM',  # Assuming all bot interactions are DM for now
            bot_classification=bot_classification,
            bot_response=bot_response_text
        )
    else:
        logger.warning("Could not log chat interaction: missing meeting_id or user_id.")
    
    return jsonify(response_data)

if __name__ == '__main__':
    initialize_rag_system()
    app.run(host='0.0.0.0', port=5000, debug=True)