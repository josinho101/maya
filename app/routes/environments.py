from flask import Blueprint, jsonify, request

from app.controllers import environments_controller
from app.middleware.auth import require_auth

bp = Blueprint("environments", __name__)


@bp.get("/projects/<project_id>/environments")
@require_auth
def list_environments(project_id):
    return jsonify(environments_controller.list_all(project_id))


@bp.post("/projects/<project_id>/environments")
@require_auth
def create_environment(project_id):
    body = request.get_json(silent=True) or {}
    return jsonify(environments_controller.create_manual(project_id, body.get("name"), body.get("url"))), 201


@bp.put("/projects/<project_id>/environments")
@require_auth
def rename_environments(project_id):
    body = request.get_json(silent=True) or {}
    return jsonify(environments_controller.rename_many(project_id, body.get("environments", [])))


@bp.delete("/projects/<project_id>/environments/<env_id>")
@require_auth
def delete_environment(project_id, env_id):
    return jsonify(environments_controller.delete(project_id, env_id))
