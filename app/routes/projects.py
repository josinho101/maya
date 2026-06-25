from flask import Blueprint, jsonify, request

from app.controllers import projects_controller
from app.middleware.auth import require_admin, require_auth

bp = Blueprint("projects", __name__)


@bp.get("/projects")
@require_auth
def list_projects():
    return jsonify(projects_controller.list_all())


@bp.post("/projects")
@require_admin
def create_project():
    data = request.get_json(silent=True) or {}
    return jsonify(projects_controller.create(data.get("name", ""), data.get("description", ""))), 201


@bp.get("/projects/<project_id>")
@require_auth
def get_project(project_id):
    return jsonify(projects_controller.get(project_id))


@bp.put("/projects/<project_id>")
@require_admin
def update_project(project_id):
    data = request.get_json(silent=True) or {}
    return jsonify(projects_controller.update(project_id, data.get("name"), data.get("description")))


@bp.delete("/projects/<project_id>")
@require_admin
def delete_project(project_id):
    return jsonify(projects_controller.delete(project_id))
