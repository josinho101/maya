from flask import Blueprint, jsonify, request

from app.controllers import scenario_jobs_controller
from app.middleware.auth import require_admin, require_auth

bp = Blueprint("scenario_jobs", __name__)


@bp.post("/projects/<project_id>/generations/<gen_id>/scenario-jobs")
@require_admin
def submit_scenario_job(project_id, gen_id):
    body = request.get_json(silent=True) or {}
    job = scenario_jobs_controller.submit_scenario_job(
        project_id,
        gen_id,
        body.get("endpoint"),
        body.get("method"),
        body.get("scenario"),
        files=body.get("files"),
    )
    return jsonify(job), 202


@bp.get("/projects/<project_id>/scenario-jobs")
@require_auth
def list_scenario_jobs(project_id):
    return jsonify(scenario_jobs_controller.list_scenario_jobs(project_id))


@bp.get("/projects/<project_id>/scenario-jobs/<job_id>")
@require_auth
def get_scenario_job(project_id, job_id):
    return jsonify(scenario_jobs_controller.get_scenario_job(project_id, job_id))


@bp.post("/projects/<project_id>/scenario-jobs/<job_id>/stop")
@require_admin
def stop_scenario_job(project_id, job_id):
    return jsonify(scenario_jobs_controller.request_stop_scenario_job(project_id, job_id)), 202
