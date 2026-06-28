from flasgger.utils import swag_from
from flask import Blueprint, jsonify, request, send_file

from app.controllers import executions_controller
from app.middleware.auth import require_auth

bp = Blueprint("executions", __name__)


@bp.post("/projects/<project_id>/generations/<gen_id>/execute")
@require_auth
@swag_from("../../docs/swagger/executions/execute_generation.yml")
def execute_generation(project_id, gen_id):
    body = request.get_json(silent=True) or {}
    return jsonify(executions_controller.execute(project_id, gen_id, environment_id=body.get("environment_id"))), 202


@bp.get("/projects/<project_id>/executions")
@require_auth
@swag_from("../../docs/swagger/executions/list_executions.yml")
def list_executions(project_id):
    return jsonify(executions_controller.list_all(project_id))


@bp.get("/projects/<project_id>/executions/<exec_id>")
@require_auth
@swag_from("../../docs/swagger/executions/get_execution.yml")
def get_execution(project_id, exec_id):
    return jsonify(executions_controller.get(project_id, exec_id))


@bp.get("/projects/<project_id>/executions/<exec_id>/report")
@swag_from("../../docs/swagger/executions/get_report.yml")
def get_report(project_id, exec_id):
    return send_file(executions_controller.get_report_path(project_id, exec_id), mimetype="text/html")


@bp.get("/projects/<project_id>/executions/<exec_id>/results")
@require_auth
@swag_from("../../docs/swagger/executions/get_results.yml")
def get_results(project_id, exec_id):
    return jsonify(executions_controller.get_results(project_id, exec_id))
