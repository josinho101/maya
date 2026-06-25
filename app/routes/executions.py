from flask import Blueprint, jsonify, send_file

from app.controllers import executions_controller
from app.middleware.auth import require_auth

bp = Blueprint("executions", __name__)


@bp.post("/projects/<project_id>/generations/<gen_id>/execute")
@require_auth
def execute_generation(project_id, gen_id):
    return jsonify(executions_controller.execute(project_id, gen_id)), 202


@bp.get("/projects/<project_id>/executions")
@require_auth
def list_executions(project_id):
    return jsonify(executions_controller.list_all(project_id))


@bp.get("/projects/<project_id>/executions/<exec_id>")
@require_auth
def get_execution(project_id, exec_id):
    return jsonify(executions_controller.get(project_id, exec_id))


@bp.get("/projects/<project_id>/executions/<exec_id>/report")
def get_report(project_id, exec_id):
    return send_file(executions_controller.get_report_path(project_id, exec_id), mimetype="text/html")


@bp.get("/projects/<project_id>/executions/<exec_id>/results")
@require_auth
def get_results(project_id, exec_id):
    return jsonify(executions_controller.get_results(project_id, exec_id))
