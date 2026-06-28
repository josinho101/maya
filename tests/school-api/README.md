# School API

A self-contained Flask test app demonstrating students, teachers, and classes with JWT auth, role-based access control, photo uploads, pagination, and OpenAPI 3.0.3 docs. All data is stored in memory and resets on every restart.

## Setup

```bash
cd tests/school-api
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

## Run

```bash
python server.py
```

The server starts on `http://localhost:8070`.

## Swagger docs

- UI: `http://localhost:8070/swagger/`
- Raw spec: `http://localhost:8070/swagger.json`

Use `POST /api/auth/login` to get a JWT, then click "Authorize" in the Swagger UI and paste the raw token (no `Bearer ` prefix needed).

## Users

| Username | Password | Role |
|---|---|---|
| admin1 | admin123 | admin |
| admin2 | admin123 | admin |
| admin3 | admin123 | admin |
| user1 | user123 | user |
| user2 | user123 | user |
| user3 | user123 | user |

Admins can create/update/delete students and teachers and upload their photos. Regular users can only view (GET) data.

## Notes

- All student/teacher/class data lives in memory and is re-seeded on every restart.
- Uploaded photos are written to `uploads/`, which is cleared on every app start.
