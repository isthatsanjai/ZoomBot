import hmac, hashlib, json, requests, logging
from config import Config
from app import APP_ACCESS_TOKEN

logger = logging.getLogger(__name__)

def verify_webhook(headers, raw_body):
    try:
        signature = headers.get('x-zm-signature')
        message = f"v0:{headers.get('x-zm-request-timestamp')}:{raw_body}"
        expected_signature = hmac.new(Config.ZOOM_WEBHOOK_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(f"v0={expected_signature}", signature)
    except Exception as e:
        logger.error(f"Webhook verification failed: {e}")
        return False

def send_chat_message(to_channel_id, message):
    if not APP_ACCESS_TOKEN:
        logger.error("No token set")
        return False

    url = "https://api.zoom.us/v2/chat/users/me/messages"
    headers = {"Authorization": f"Bearer {APP_ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"to_channel": to_channel_id, "message": message}
    response = requests.post(url, headers=headers, json=payload)

    return response.status_code == 201