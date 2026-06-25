from flask import Blueprint, jsonify, request

from app.controllers import generations_controller
from app.middleware.auth import require_admin, require_auth

bp = Blueprint("generations", __name__)


@bp.post("/projects/<project_id>/generate")
@require_admin
def trigger_generation(project_id):
    body = request.get_json(silent=True) or {}
    return jsonify(generations_controller.trigger(project_id, body.get("endpoints_to_regenerate"))), 202


@bp.get("/projects/<project_id>/generations")
@require_auth
def list_generations(project_id):
    return jsonify(generations_controller.list_all(project_id))


@bp.get("/projects/<project_id>/generations/<gen_id>")
@require_auth
def get_generation(project_id, gen_id):
    return jsonify(generations_controller.get(project_id, gen_id))


@bp.post("/projects/<project_id>/generations/<gen_id>/testcases")
@require_admin
def add_testcase(project_id, gen_id):
    body = request.get_json(silent=True) or {}
    endpoint = body.get("endpoint")
    method = body.get("method")
    new_tc = {k: v for k, v in body.items() if k not in ("endpoint", "method")}
    return jsonify(
        generations_controller.add_testcase(project_id, gen_id, endpoint, method, new_tc, needs_review=False)
    ), 201


@bp.put("/projects/<project_id>/generations/<gen_id>/testcases/<tc_id>")
@require_admin
def edit_testcase(project_id, gen_id, tc_id):
    updated_tc = request.get_json(silent=True)
    return jsonify(generations_controller.edit_testcase(project_id, gen_id, tc_id, updated_tc))


@bp.delete("/projects/<project_id>/generations/<gen_id>/testcases/<tc_id>")
@require_admin
def delete_testcase(project_id, gen_id, tc_id):
    return jsonify(generations_controller.delete_testcase(project_id, gen_id, tc_id))


@bp.post("/projects/<project_id>/generations/<gen_id>/testcases/<tc_id>/approve")
@require_admin
def approve_testcase(project_id, gen_id, tc_id):
    return jsonify(generations_controller.approve_testcase(project_id, gen_id, tc_id))


@bp.post("/projects/<project_id>/generations/<gen_id>/approve")
@require_admin
def approve_generation(project_id, gen_id):
    return jsonify(generations_controller.approve(project_id, gen_id))


@bp.get("/projects/<project_id>/generations/<gen_id>/testcases/sample")
@require_admin
def get_testcase_sample(project_id, gen_id):
    endpoint = request.args.get("endpoint")
    method = request.args.get("method")
    return jsonify(generations_controller.get_sample_testcase(project_id, gen_id, endpoint, method))


@bp.post("/projects/<project_id>/generations/<gen_id>/testcase-files")
@require_admin
def upload_testcase_file(project_id, gen_id):
    file_storage = request.files.get("file")
    return jsonify(generations_controller.upload_testcase_file(project_id, gen_id, file_storage)), 201


@bp.post("/projects/<project_id>/generations/<gen_id>/stop")
@require_admin
def stop_generation(project_id, gen_id):
    return jsonify(generations_controller.request_stop_generation(project_id, gen_id)), 202
