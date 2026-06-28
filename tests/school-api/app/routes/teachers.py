from flasgger.utils import swag_from
from flask import Blueprint, jsonify, request

from app.controllers import BadRequest, teachers_controller
from app.middleware.auth import require_admin, require_auth

bp = Blueprint("teachers", __name__)


@bp.get("/teachers")
@require_auth
@swag_from("../../docs/swagger/teachers/list_teachers.yml")
def list_teachers():
    return jsonify(teachers_controller.list_all(request.args))


@bp.post("/teachers")
@require_admin
@swag_from("../../docs/swagger/teachers/create_teacher.yml")
def create_teacher():
    data = request.get_json(silent=True) or {}
    return jsonify(teachers_controller.create(data)), 201


@bp.get("/teachers/<teacher_id>")
@require_auth
@swag_from("../../docs/swagger/teachers/get_teacher.yml")
def get_teacher(teacher_id):
    return jsonify(teachers_controller.get(teacher_id))


@bp.put("/teachers/<teacher_id>")
@require_admin
@swag_from("../../docs/swagger/teachers/update_teacher.yml")
def update_teacher(teacher_id):
    data = request.get_json(silent=True) or {}
    return jsonify(teachers_controller.update(teacher_id, data))


@bp.delete("/teachers/<teacher_id>")
@require_admin
@swag_from("../../docs/swagger/teachers/delete_teacher.yml")
def delete_teacher(teacher_id):
    return jsonify(teachers_controller.delete(teacher_id))


@bp.post("/teachers/<teacher_id>/photo")
@require_admin
@swag_from("../../docs/swagger/teachers/upload_teacher_photo.yml")
def upload_teacher_photo(teacher_id):
    file = request.files.get("photo")
    if not file:
        raise BadRequest("photo file is required")
    teacher = teachers_controller.save_photo(teacher_id, file)
    return jsonify({"photo_url": teacher["photo_url"]})
