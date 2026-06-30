from app.controllers import BadRequest, NotFound
from app.controllers.environments_controller import list_all as list_environments
from app.controllers.projects_controller import find_project
from app.storage.json_store import data_path, load_json, new_id, save_json


def _tu_path(slug):
    return data_path(slug, "test_users.json")


def _load(slug):
    return load_json(_tu_path(slug), default=[])


def _save(slug, users):
    save_json(_tu_path(slug), users)


def _require_project_and_env(project_id, env_id):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")
    if not any(e["id"] == env_id for e in list_environments(project_id)):
        raise NotFound("environment not found")
    return p["slug"]


def _normalize_roles(roles):
    if isinstance(roles, str):
        roles = roles.split(",")
    return [r.strip() for r in (roles or []) if isinstance(r, str) and r.strip()]


def _with_roles(user):
    # Legacy entries stored a single "role" string; normalize to "roles" on read.
    if "roles" not in user:
        user["roles"] = _normalize_roles(user.pop("role", None))
    return user


def list_for_env(project_id, env_id):
    slug = _require_project_and_env(project_id, env_id)
    return [_with_roles(u) for u in _load(slug) if u["environment_id"] == env_id]


def create(project_id, env_id, username, password, roles):
    slug = _require_project_and_env(project_id, env_id)

    username = (username or "").strip()
    password = password or ""
    roles = _normalize_roles(roles)
    if not username or not password:
        raise BadRequest("username and password are required")

    users = _load(slug)
    users.append({
        "id": new_id(),
        "environment_id": env_id,
        "username": username,
        "password": password,
        "roles": roles,
    })
    _save(slug, users)

    return [_with_roles(u) for u in users if u["environment_id"] == env_id]


def update(project_id, env_id, user_id, username, password, roles):
    slug = _require_project_and_env(project_id, env_id)

    users = _load(slug)
    user = next((u for u in users if u["id"] == user_id and u["environment_id"] == env_id), None)
    if user is None:
        raise NotFound("test user not found")

    username = (username or "").strip()
    if not username:
        raise BadRequest("username is required")

    user["username"] = username
    if password:
        user["password"] = password
    user.pop("role", None)
    user["roles"] = _normalize_roles(roles)

    _save(slug, users)

    return [_with_roles(u) for u in users if u["environment_id"] == env_id]


def delete(project_id, env_id, user_id):
    slug = _require_project_and_env(project_id, env_id)

    users = _load(slug)
    if not any(u["id"] == user_id and u["environment_id"] == env_id for u in users):
        raise NotFound("test user not found")

    users = [u for u in users if u["id"] != user_id]
    _save(slug, users)

    return [_with_roles(u) for u in users if u["environment_id"] == env_id]
