from flask import Blueprint, jsonify, request

from app.controllers import auth_controller
from app.middleware.auth import get_current_user, require_auth

bp = Blueprint("auth", __name__)


@bp.post("/auth/login")
def login():
    body = request.get_json(silent=True) or {}
    return jsonify(auth_controller.login(body.get("username", ""), body.get("password", "")))


@bp.get("/auth/me")
@require_auth
def me():
    user = get_current_user()
    return jsonify({"username": user["username"], "role": user["role"]})
