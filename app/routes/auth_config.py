from flasgger.utils import swag_from
from flask import Blueprint, jsonify, request

from app.controllers import auth_config_controller
from app.middleware.auth import require_admin, require_auth

bp = Blueprint("auth_config", __name__)

_BASE = "/projects/<project_id>/environments/<env_id>/auth-config"


@bp.get(_BASE)
@require_auth
@swag_from("../../docs/swagger/auth_config/get_auth_config.yml")
def get_auth_config(project_id, env_id):
    return jsonify(auth_config_controller.get(project_id, env_id))


@bp.put(_BASE)
@require_admin
@swag_from("../../docs/swagger/auth_config/save_auth_config.yml")
def save_auth_config(project_id, env_id):
    body = request.get_json(silent=True) or {}
    return jsonify(auth_config_controller.save(project_id, env_id, body))


@bp.post(f"{_BASE}/test")
@require_auth
@swag_from("../../docs/swagger/auth_config/test_auth_config.yml")
def test_auth_config(project_id, env_id):
    body = request.get_json(silent=True) or {}
    return jsonify(auth_config_controller.test_login(project_id, env_id, body))
