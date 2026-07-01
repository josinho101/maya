from flasgger.utils import swag_from
from flask import Blueprint, jsonify, request

from app.controllers import settings_controller
from app.middleware.auth import require_admin, require_auth

bp = Blueprint("settings", __name__)

_BASE = "/projects/<project_id>/environments/<env_id>/settings"


@bp.get(_BASE)
@require_auth
@swag_from("../../docs/swagger/settings/get_settings.yml")
def get_settings(project_id, env_id):
    return jsonify(settings_controller.get(project_id, env_id))


@bp.put(_BASE)
@require_admin
@swag_from("../../docs/swagger/settings/save_settings.yml")
def save_settings(project_id, env_id):
    body = request.get_json(silent=True) or {}
    return jsonify(settings_controller.save(project_id, env_id, body))


@bp.post(f"{_BASE}/auth/test")
@require_auth
@swag_from("../../docs/swagger/settings/test_auth.yml")
def test_auth(project_id, env_id):
    body = request.get_json(silent=True) or {}
    return jsonify(settings_controller.test_auth(project_id, env_id, body))
