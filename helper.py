import os
import jwt
from datetime import datetime

def JWT_generator(meeting_id: int = 89218685071):
    header = {
        "alg": "HS256",
        "typ": "JWT"
    }

    time_now = int(datetime.now().timestamp())

    payload = {
        "appKey": os.environ['ZOOM_SDK_KEY'],
        "mn": meeting_id,
        "role": 0,
        "iat": time_now,
        "exp": time_now + 7200,
        "tokenExp": time_now + 7200
    }

    print(payload, meeting_id)

    return jwt.encode(payload, os.environ['ZOOM_SDK_SECRET'], algorithm="HS256", headers=header)
print(JWT_generator())