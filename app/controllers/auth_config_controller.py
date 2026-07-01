import json

import requests as http_requests

from app.controllers import BadRequest, NotFound
from app.controllers.environments_controller import list_all as list_environments
from app.controllers.projects_controller import find_project
from app.controllers.test_users_controller import list_for_env
from app.storage.json_store import data_path, load_json, save_json

VALID_AUTH_TYPES = {"none", "bearer_login"}

_DEFAULTS = {
    "auth_type": "none",
    "auth_endpoint": "",
    "request_body_template": '{"username": "{{username}}", "password": "{{password}}"}',
    "token_path": "token",
}


def _configs_path(slug):
    return data_path(slug, "auth_configs.json")


def _require_project_and_env(project_id, env_id):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")
    if not any(e["id"] == env_id for e in list_environments(project_id)):
        raise NotFound("environment not found")
    return p["slug"]


def get(project_id, env_id):
    slug = _require_project_and_env(project_id, env_id)
    all_configs = load_json(_configs_path(slug), default={})
    return {**_DEFAULTS, **all_configs.get(env_id, {})}


def save(project_id, env_id, config):
    slug = _require_project_and_env(project_id, env_id)

    auth_type = (config.get("auth_type") or "none").strip()
    if auth_type not in VALID_AUTH_TYPES:
        raise BadRequest(f"Invalid auth_type '{auth_type}': must be one of {sorted(VALID_AUTH_TYPES)}")

    to_store = {
        "auth_type": auth_type,
        "auth_endpoint": (config.get("auth_endpoint") or "").strip(),
        "request_body_template": config.get("request_body_template") or _DEFAULTS["request_body_template"],
        "token_path": (config.get("token_path") or "token").strip(),
    }

    all_configs = load_json(_configs_path(slug), default={})
    all_configs[env_id] = to_store
    save_json(_configs_path(slug), all_configs)
    return to_store


def _resolve_path(data, dot_path):
    """Walk a dot-separated path through a nested dict. Returns (value, found)."""
    current = data
    for part in dot_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None, False
        current = current[part]
    return current, True


def test_login(project_id, env_id, config):
    """Fire the configured login request using the first test user. Always returns a result dict."""
    if config.get("auth_type") != "bearer_login":
        return {"success": False, "message": "Auth type is not Bearer Token"}

    try:
        users = list_for_env(project_id, env_id)
    except Exception:
        users = []

    if not users:
        return {"success": False, "message": "No test users configured for this environment. Add one in the Test Users tab first."}

    user = users[0]
    auth_endpoint = (config.get("auth_endpoint") or "").strip()
    if not auth_endpoint:
        return {"success": False, "message": "Auth endpoint is not configured"}

    template = config.get("request_body_template") or _DEFAULTS["request_body_template"]
    body_str = template.replace("{{username}}", user.get("username", "")).replace("{{password}}", user.get("password", ""))

    try:
        body = json.loads(body_str)
    except json.JSONDecodeError as e:
        return {"success": False, "message": f"Invalid JSON in request body template: {e}"}

    try:
        resp = http_requests.post(auth_endpoint, json=body, timeout=10)
    except http_requests.exceptions.ConnectionError as e:
        return {"success": False, "message": f"Connection failed: {e}"}
    except http_requests.exceptions.Timeout:
        return {"success": False, "message": "Request timed out after 10 seconds"}
    except Exception as e:
        return {"success": False, "message": f"Request error: {e}"}

    try:
        resp_body = resp.json()
    except Exception:
        resp_body = resp.text

    token_path = (config.get("token_path") or "token").strip()
    token, found = _resolve_path(resp_body if isinstance(resp_body, dict) else {}, token_path)

    if found and token:
        token_str = str(token)
        return {
            "success": True,
            "status_code": resp.status_code,
            "message": f"Token extracted at path '{token_path}'",
            "token_preview": token_str[:30] + ("..." if len(token_str) > 30 else ""),
            "response_body": resp_body,
        }

    return {
        "success": False,
        "status_code": resp.status_code,
        "message": f"Token not found at path '{token_path}' — check token path against the response below",
        "response_body": resp_body,
    }
