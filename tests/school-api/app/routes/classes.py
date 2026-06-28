from flasgger.utils import swag_from
from flask import Blueprint, jsonify

from app.controllers import classes_controller
from app.middleware.auth import require_auth

bp = Blueprint("classes", __name__)


@bp.get("/classes")
@require_auth
@swag_from("../../docs/swagger/classes/list_classes.yml")
def list_classes():
    return jsonify(classes_controller.list_all())


@bp.get("/classes/<class_id>")
@require_auth
@swag_from("../../docs/swagger/classes/get_class.yml")
def get_class(class_id):
    return jsonify(classes_controller.get(class_id))


@bp.get("/classes/<class_id>/students")
@require_auth
@swag_from("../../docs/swagger/classes/list_class_students.yml")
def list_class_students(class_id):
    return jsonify(classes_controller.list_students_in_class(class_id))
