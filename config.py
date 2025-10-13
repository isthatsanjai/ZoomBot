import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # --- Zoom OAuth App Credentials (for API access like file upload) ---
    ZOOM_CLIENT_ID = os.getenv('ZOOM_CLIENT_ID')
    ZOOM_CLIENT_SECRET = os.getenv('ZOOM_CLIENT_SECRET')
    ZOOM_REDIRECT_URI = os.getenv('ZOOM_REDIRECT_URI') # e.g., http://localhost:5000/auth

    # --- Zoom Meeting SDK App Credentials (for joining meetings) ---
    # IMPORTANT: Get these from your "Meeting SDK" app on the Zoom Marketplace
    ZOOM_SDK_KEY = os.getenv('ZOOM_SDK_KEY')
    ZOOM_SDK_SECRET = os.getenv('ZOOM_SDK_SECRET')

    # --- OpenAI Credentials ---
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

    # --- Application Settings ---
    UPLOAD_FOLDER = 'uploads'
    TOKEN_FILE = "zoom_tokens.json"

     # --- NEW: PostgreSQL Database Configuration ---
    DB_NAME = os.getenv('DB_NAME')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_HOST = os.getenv('DB_HOST')
    DB_PORT = os.getenv('DB_PORT')