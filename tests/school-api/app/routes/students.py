from flasgger.utils import swag_from
from flask import Blueprint, jsonify, request

from app.controllers import BadRequest, students_controller
from app.middleware.auth import require_admin, require_auth

bp = Blueprint("students", __name__)


@bp.get("/students")
@require_auth
@swag_from("../../docs/swagger/students/list_students.yml")
def list_students():
    return jsonify(students_controller.list_all(request.args))


@bp.post("/students")
@require_admin
@swag_from("../../docs/swagger/students/create_student.yml")
def create_student():
    data = request.get_json(silent=True) or {}
    return jsonify(students_controller.create(data)), 201


@bp.get("/students/<student_id>")
@require_auth
@swag_from("../../docs/swagger/students/get_student.yml")
def get_student(student_id):
    return jsonify(students_controller.get(student_id))


@bp.put("/students/<student_id>")
@require_admin
@swag_from("../../docs/swagger/students/update_student.yml")
def update_student(student_id):
    data = request.get_json(silent=True) or {}
    return jsonify(students_controller.update(student_id, data))


@bp.delete("/students/<student_id>")
@require_admin
@swag_from("../../docs/swagger/students/delete_student.yml")
def delete_student(student_id):
    return jsonify(students_controller.delete(student_id))


@bp.post("/students/<student_id>/photo")
@require_admin
@swag_from("../../docs/swagger/students/upload_student_photo.yml")
def upload_student_photo(student_id):
    file = request.files.get("photo")
    if not file:
        raise BadRequest("photo file is required")
    student = students_controller.save_photo(student_id, file)
    return jsonify({"photo_url": student["photo_url"]})
