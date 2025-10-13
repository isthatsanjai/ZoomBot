import os
import json
import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from config import Config

logger = logging.getLogger(__name__)

APP_ACCESS_TOKEN = None
REFRESH_TOKEN = None
TOKEN_EXPIRY = None

def save_tokens_to_file(token_data: Dict[str, Any]):
    """Saves token data to a file."""
    try:
        with open(Config.TOKEN_FILE, "w") as f:
            json.dump(token_data, f)
        logger.info(f"Tokens saved to {Config.TOKEN_FILE}")
    except Exception as e:
        logger.error(f"Error saving tokens to file: {e}")

def load_tokens_from_file():
    """Loads tokens from a file and populates global variables."""
    global APP_ACCESS_TOKEN, REFRESH_TOKEN, TOKEN_EXPIRY
    try:
        if not os.path.exists(Config.TOKEN_FILE):
            logger.info(f"{Config.TOKEN_FILE} not found. App will need authorization.")
            return

        with open(Config.TOKEN_FILE, "r") as f:
            token_data = json.load(f)
            APP_ACCESS_TOKEN = token_data.get("access_token")
            REFRESH_TOKEN = token_data.get("refresh_token")
            if token_data.get("token_expiry_iso"):
                TOKEN_EXPIRY = datetime.fromisoformat(token_data["token_expiry_iso"])
            
            if APP_ACCESS_TOKEN:
                logger.info(f">>> Successfully loaded tokens from {Config.TOKEN_FILE} <<<")
    except Exception as e:
        logger.error(f"Error loading tokens from file: {e}")

def refresh_access_token():
    """Refreshes the OAuth access token."""
    global APP_ACCESS_TOKEN, REFRESH_TOKEN, TOKEN_EXPIRY
    if not REFRESH_TOKEN:
        logger.error("No refresh token available. Re-authorization is required.")
        return False
    
    try:
        response = requests.post(
            "https://zoom.us/oauth/token",
            auth=(Config.ZOOM_CLIENT_ID, Config.ZOOM_CLIENT_SECRET),
            data={"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN}
        )
        response.raise_for_status()
        
        token_data = response.json()
        APP_ACCESS_TOKEN = token_data['access_token']
        REFRESH_TOKEN = token_data.get('refresh_token', REFRESH_TOKEN)
        TOKEN_EXPIRY = datetime.now(timezone.utc) + timedelta(seconds=token_data['expires_in'])
        
        logger.info("OAuth token refreshed successfully.")
        save_tokens_to_file({
            "access_token": APP_ACCESS_TOKEN,
            "refresh_token": REFRESH_TOKEN,
            "token_expiry_iso": TOKEN_EXPIRY.isoformat()
        })
        return True
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        return False

def ensure_valid_token():
    """Checks if the token is valid and refreshes it if necessary."""
    if not APP_ACCESS_TOKEN:
        logger.error("No access token found.")
        return False
    if TOKEN_EXPIRY and datetime.now(timezone.utc) >= TOKEN_EXPIRY - timedelta(minutes=5):
        logger.info("Token is expiring soon, refreshing...")
        return refresh_access_token()
    return True