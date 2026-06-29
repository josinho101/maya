from functools import wraps

import jwt
from flask import jsonify, request

from app import settings


def get_current_user():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    try:
        return jwt.decode(token, settings.JWT["secret_key"], algorithms=[settings.JWT["algorithm"]])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not settings.AUTH_ENABLED:
            return f(*args, **kwargs)
        if get_current_user() is None:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not settings.AUTH_ENABLED:
            return f(*args, **kwargs)
        user = get_current_user()
        if user is None:
            return jsonify({"error": "Authentication required"}), 401
        if user.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated
