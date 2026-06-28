import os
import re

from app import settings
from app.controllers import BadRequest, NotFound, paginate
from app.controllers.classes_controller import find_class
from app.storage import memory_store

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _find(student_id):
    return next((s for s in memory_store.students if s["id"] == student_id), None)


def _validate(data, existing_id=None):
    name = (data.get("name") or "").strip()
    if not name:
        raise BadRequest("name is required")

    email = (data.get("email") or "").strip().lower()
    if not email or not EMAIL_RE.match(email):
        raise BadRequest("a valid email is required")

    duplicate = next(
        (s for s in memory_store.students if s["email"].lower() == email and s["id"] != existing_id),
        None,
    )
    if duplicate:
        raise BadRequest("email already in use")

    age = data.get("age")
    if age is not None:
        if not isinstance(age, int) or isinstance(age, bool) or age <= 0:
            raise BadRequest("age must be a positive integer")

    class_id = data.get("class_id")
    if class_id is not None and not find_class(class_id):
        raise BadRequest("class_id does not reference an existing class")

    return name, email, age, class_id


def list_all(args):
    return paginate(memory_store.students, args)


def get(student_id):
    student = _find(student_id)
    if not student:
        raise NotFound("Student not found")
    return student


def create(data):
    name, email, age, class_id = _validate(data)

    student = {
        "id": memory_store.new_student_id(),
        "name": name,
        "email": email,
        "age": age,
        "class_id": class_id,
        "photo_url": None,
    }
    memory_store.students.append(student)
    return student


def update(student_id, data):
    student = _find(student_id)
    if not student:
        raise NotFound("Student not found")

    name, email, age, class_id = _validate(data, existing_id=student_id)

    student["name"] = name
    student["email"] = email
    student["age"] = age
    student["class_id"] = class_id
    return student


def delete(student_id):
    student = _find(student_id)
    if not student:
        raise NotFound("Student not found")

    if student.get("photo_url"):
        _delete_photo_file(student_id)

    memory_store.students.remove(student)
    return {"deleted": student_id}


def _photo_filename_prefix(student_id):
    return f"student_{student_id}."


def _delete_photo_file(student_id):
    prefix = _photo_filename_prefix(student_id)
    if not os.path.isdir(settings.UPLOADS_DIR):
        return
    for filename in os.listdir(settings.UPLOADS_DIR):
        if filename.startswith(prefix):
            os.remove(os.path.join(settings.UPLOADS_DIR, filename))


def save_photo(student_id, file):
    student = _find(student_id)
    if not student:
        raise NotFound("Student not found")

    if not file or not file.filename:
        raise BadRequest("photo file is required")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in settings.ALLOWED_PHOTO_EXTENSIONS:
        raise BadRequest("photo must be a jpg, jpeg, or png file")

    if file.mimetype and file.mimetype not in settings.ALLOWED_PHOTO_CONTENT_TYPES:
        raise BadRequest("photo must be a jpg, jpeg, or png file")

    _delete_photo_file(student_id)

    os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
    filename = f"{_photo_filename_prefix(student_id)}{ext}"
    file.save(os.path.join(settings.UPLOADS_DIR, filename))

    student["photo_url"] = f"/uploads/{filename}"
    return student
