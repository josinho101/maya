from app import settings
from app.controllers import NotFound
from app.storage import memory_store


def list_all():
    return settings.CLASSES


def find_class(class_id):
    return next((c for c in settings.CLASSES if c["id"] == class_id), None)


def get(class_id):
    klass = find_class(class_id)
    if not klass:
        raise NotFound("Class not found")
    return klass


def list_students_in_class(class_id):
    if not find_class(class_id):
        raise NotFound("Class not found")
    return [s for s in memory_store.students if s["class_id"] == class_id]
