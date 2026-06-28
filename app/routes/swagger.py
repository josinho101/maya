from flasgger.utils import swag_from
from flask import Blueprint, jsonify, request

from app.controllers import swagger_controller
from app.middleware.auth import require_admin, require_auth

bp = Blueprint("swagger", __name__)


@bp.post("/projects/<project_id>/swagger")
@require_admin
@swag_from("../../docs/swagger/swagger/upload_swagger.yml")
def upload_swagger(project_id):
    return jsonify(swagger_controller.upload(project_id, request.files.get("file"))), 201


@bp.post("/projects/<project_id>/swagger/url")
@require_admin
@swag_from("../../docs/swagger/swagger/import_swagger_from_url.yml")
def import_swagger_from_url(project_id):
    body = request.get_json(silent=True) or {}
    return jsonify(swagger_controller.import_from_url(project_id, body.get("url", ""))), 201


@bp.get("/projects/<project_id>/swagger")
@require_auth
@swag_from("../../docs/swagger/swagger/get_swagger.yml")
def get_swagger(project_id):
    return jsonify(swagger_controller.get(project_id))
