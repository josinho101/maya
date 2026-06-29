import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

# Toggle authentication on/off. When False, all endpoints bypass auth checks.
AUTH_ENABLED = True

# User accounts — hardcoded for this test app. role must be "admin" or "user".
USERS = [
    {"username": "admin1", "password": "admin123", "role": "admin"},
    {"username": "admin2", "password": "admin123", "role": "admin"},
    {"username": "admin3", "password": "admin123", "role": "admin"},
    {"username": "user1", "password": "user123", "role": "user"},
    {"username": "user2", "password": "user123", "role": "user"},
    {"username": "user3", "password": "user123", "role": "user"},
]

JWT = {
    "secret_key": "change-me-in-production",
    "algorithm": "HS256",
    "expiry_hours": 24,
}

# Hardcoded list of 10 classes. Read-only for the lifetime of the app.
CLASSES = [
    {"id": "C1", "name": "Class 1", "subject": "Mathematics", "teacher_id": "T1"},
    {"id": "C2", "name": "Class 2", "subject": "Science", "teacher_id": "T2"},
    {"id": "C3", "name": "Class 3", "subject": "English", "teacher_id": "T3"},
    {"id": "C4", "name": "Class 4", "subject": "History", "teacher_id": "T4"},
    {"id": "C5", "name": "Class 5", "subject": "Art", "teacher_id": "T1"},
    {"id": "C6", "name": "Class 6", "subject": "Music", "teacher_id": "T2"},
    {"id": "C7", "name": "Class 7", "subject": "Physical Education", "teacher_id": "T3"},
    {"id": "C8", "name": "Class 8", "subject": "Computer Science", "teacher_id": "T4"},
    {"id": "C9", "name": "Class 9", "subject": "Geography", "teacher_id": "T1"},
    {"id": "C10", "name": "Class 10", "subject": "Biology", "teacher_id": "T2"},
]

ALLOWED_PHOTO_EXTENSIONS = {"jpg", "jpeg", "png"}
ALLOWED_PHOTO_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png"}

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 10
