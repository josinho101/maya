from flasgger.utils import swag_from
from flask import Blueprint, jsonify, request

from app.controllers import projects_controller
from app.middleware.auth import require_admin, require_auth

bp = Blueprint("projects", __name__)


@bp.get("/projects")
@require_auth
@swag_from("../../docs/swagger/projects/list_projects.yml")
def list_projects():
    return jsonify(projects_controller.list_all())


@bp.post("/projects")
@require_admin
@swag_from("../../docs/swagger/projects/create_project.yml")
def create_project():
    data = request.get_json(silent=True) or {}
    return jsonify(projects_controller.create(data.get("name", ""), data.get("description", ""))), 201


@bp.get("/projects/<project_id>")
@require_auth
@swag_from("../../docs/swagger/projects/get_project.yml")
def get_project(project_id):
    return jsonify(projects_controller.get(project_id))


@bp.put("/projects/<project_id>")
@require_admin
@swag_from("../../docs/swagger/projects/update_project.yml")
def update_project(project_id):
    data = request.get_json(silent=True) or {}
    return jsonify(projects_controller.update(project_id, data.get("name"), data.get("description")))


@bp.delete("/projects/<project_id>")
@require_admin
@swag_from("../../docs/swagger/projects/delete_project.yml")
def delete_project(project_id):
    return jsonify(projects_controller.delete(project_id))
