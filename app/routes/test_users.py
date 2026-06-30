from flasgger.utils import swag_from
from flask import Blueprint, jsonify, request

from app.controllers import test_users_controller
from app.middleware.auth import require_auth

bp = Blueprint("test_users", __name__)

_BASE = "/projects/<project_id>/environments/<env_id>/test_users"


@bp.get(_BASE)
@require_auth
@swag_from("../../docs/swagger/test_users/list_test_users.yml")
def list_test_users(project_id, env_id):
    return jsonify(test_users_controller.list_for_env(project_id, env_id))


@bp.post(_BASE)
@require_auth
@swag_from("../../docs/swagger/test_users/create_test_user.yml")
def create_test_user(project_id, env_id):
    body = request.get_json(silent=True) or {}
    result = test_users_controller.create(
        project_id, env_id, body.get("username"), body.get("password"), body.get("roles")
    )
    return jsonify(result), 201


@bp.put(f"{_BASE}/<user_id>")
@require_auth
@swag_from("../../docs/swagger/test_users/update_test_user.yml")
def update_test_user(project_id, env_id, user_id):
    body = request.get_json(silent=True) or {}
    result = test_users_controller.update(
        project_id, env_id, user_id, body.get("username"), body.get("password"), body.get("roles")
    )
    return jsonify(result)


@bp.delete(f"{_BASE}/<user_id>")
@require_auth
@swag_from("../../docs/swagger/test_users/delete_test_user.yml")
def delete_test_user(project_id, env_id, user_id):
    return jsonify(test_users_controller.delete(project_id, env_id, user_id))
