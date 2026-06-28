import os
import re

from app import settings
from app.controllers import BadRequest, NotFound, paginate
from app.storage import memory_store

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _find(teacher_id):
    return next((t for t in memory_store.teachers if t["id"] == teacher_id), None)


def _validate(data, existing_id=None):
    name = (data.get("name") or "").strip()
    if not name:
        raise BadRequest("name is required")

    email = (data.get("email") or "").strip().lower()
    if not email or not EMAIL_RE.match(email):
        raise BadRequest("a valid email is required")

    duplicate = next(
        (t for t in memory_store.teachers if t["email"].lower() == email and t["id"] != existing_id),
        None,
    )
    if duplicate:
        raise BadRequest("email already in use")

    subject = (data.get("subject") or "").strip()
    if not subject:
        raise BadRequest("subject is required")

    return name, email, subject


def list_all(args):
    return paginate(memory_store.teachers, args)


def get(teacher_id):
    teacher = _find(teacher_id)
    if not teacher:
        raise NotFound("Teacher not found")
    return teacher


def create(data):
    name, email, subject = _validate(data)

    teacher = {
        "id": memory_store.new_teacher_id(),
        "name": name,
        "email": email,
        "subject": subject,
        "photo_url": None,
    }
    memory_store.teachers.append(teacher)
    return teacher


def update(teacher_id, data):
    teacher = _find(teacher_id)
    if not teacher:
        raise NotFound("Teacher not found")

    name, email, subject = _validate(data, existing_id=teacher_id)

    teacher["name"] = name
    teacher["email"] = email
    teacher["subject"] = subject
    return teacher


def delete(teacher_id):
    teacher = _find(teacher_id)
    if not teacher:
        raise NotFound("Teacher not found")

    if teacher.get("photo_url"):
        _delete_photo_file(teacher_id)

    memory_store.teachers.remove(teacher)
    return {"deleted": teacher_id}


def _photo_filename_prefix(teacher_id):
    return f"teacher_{teacher_id}."


def _delete_photo_file(teacher_id):
    prefix = _photo_filename_prefix(teacher_id)
    if not os.path.isdir(settings.UPLOADS_DIR):
        return
    for filename in os.listdir(settings.UPLOADS_DIR):
        if filename.startswith(prefix):
            os.remove(os.path.join(settings.UPLOADS_DIR, filename))


def save_photo(teacher_id, file):
    teacher = _find(teacher_id)
    if not teacher:
        raise NotFound("Teacher not found")

    if not file or not file.filename:
        raise BadRequest("photo file is required")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in settings.ALLOWED_PHOTO_EXTENSIONS:
        raise BadRequest("photo must be a jpg, jpeg, or png file")

    if file.mimetype and file.mimetype not in settings.ALLOWED_PHOTO_CONTENT_TYPES:
        raise BadRequest("photo must be a jpg, jpeg, or png file")

    _delete_photo_file(teacher_id)

    os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
    filename = f"{_photo_filename_prefix(teacher_id)}{ext}"
    file.save(os.path.join(settings.UPLOADS_DIR, filename))

    teacher["photo_url"] = f"/uploads/{filename}"
    return teacher
