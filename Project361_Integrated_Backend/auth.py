"""
auth.py

Firebase Authentication integration for the Heart Rate Monitoring API.

Verifies Firebase ID tokens issued by the client SDK (web/Flutter/mobile).
The mobile/web app signs the user in via Firebase Auth, gets an ID token,
and sends it in the `Authorization: Bearer <token>` header. This module
verifies the token server-side using the Firebase Admin SDK.

If Firebase Auth is unavailable (no credentials / not initialised), auth
falls back to the legacy X-Device-Token scheme so the prototype still
works for the ESP32 wearable.

Usage in a Flask route:
    from auth import require_auth, DEVICE_TOKEN, AUTHORIZATION
    @app.route('/protected')
    def protected():
        auth = require_auth()  # raises 401 if invalid
        # auth = {'uid': ..., 'email': ..., 'name': ...}
"""

from functools import wraps
from flask import request, jsonify

from firebase_config import get_auth, is_firebase_available

DEVICE_TOKEN = "prj361-esp32-token"
AUTHORIZATION_HEADER = "Authorization"
DEVICE_TOKEN_HEADER = "X-Device-Token"


def verify_id_token(token: str) -> dict | None:
    """
    Verifies a Firebase ID token using the Admin SDK.
    Returns the decoded token claims (dict) if valid, else None.
    """
    auth = get_auth()
    if not auth or not is_firebase_available():
        return None
    try:
        decoded = auth.verify_id_token(token, check_revoked=False)
        return decoded
    except Exception:
        return None


def resolve_auth():
    """
    Resolves the caller's identity from the request.
    Returns a dict describing how the client authenticated.

    Priority:
        1. Firebase ID token (Authorization: Bearer <token>)
        2. Legacy device token (X-Device-Token header)
    """
    auth_header = request.headers.get(AUTHORIZATION_HEADER, "")
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):].strip()
        claims = verify_id_token(token)
        if claims:
            return {
                "authenticated": True,
                "method": "firebase",
                "uid": claims.get("uid"),
                "email": claims.get("email"),
                "name": claims.get("name"),
            }
        return {"authenticated": False, "method": "firebase", "reason": "invalid_token"}

    device_token = request.headers.get(DEVICE_TOKEN_HEADER)
    if device_token == DEVICE_TOKEN:
        return {"authenticated": True, "method": "device_token"}

    return {"authenticated": False, "method": "none", "reason": "missing_credentials"}


def require_auth(allowed_methods=("firebase", "device_token")):
    """
    Decorator requiring a valid auth credential.
    If a Firebase ID token is present it is verified; otherwise the
    legacy device token is checked. Returns the auth dict on success or
    a 401 JSON response on failure.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            auth = resolve_auth()
            if not auth["authenticated"] or auth["method"] not in allowed_methods:
                return jsonify({
                    "status": "error",
                    "message": "Unauthorized — provide a valid Firebase ID token "
                               "or X-Device-Token header.",
                }), 401
            return func(*args, auth=auth, **kwargs)
        return wrapper
    return decorator
