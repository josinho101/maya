import json

import requests as http_requests

from app.controllers import BadRequest, NotFound
from app.controllers.environments_controller import list_all as list_environments
from app.controllers.projects_controller import find_project
from app.controllers.test_users_controller import list_for_env
from app.storage.json_store import data_path, load_json, save_json

VALID_AUTH_TYPES = {"none", "bearer_login"}

_AUTH_DEFAULTS = {
    "auth_type": "none",
    "auth_endpoint": "",
    "request_body_template": '{"username": "{{username}}", "password": "{{password}}"}',
    "token_path": "token",
}


def _settings_path(slug):
    return data_path(slug, "settings.json")


def _legacy_auth_path(slug):
    return data_path(slug, "auth_configs.json")


def _require_project_and_env(project_id, env_id):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")
    if not any(e["id"] == env_id for e in list_environments(project_id)):
        raise NotFound("environment not found")
    return p["slug"]


def _load_env_settings(slug, env_id):
    """Load env settings, migrating from legacy auth_configs.json if needed."""
    all_settings = load_json(_settings_path(slug), default={})
    if env_id in all_settings:
        return all_settings[env_id]

    # One-time migration: promote legacy auth config into the new shape
    legacy = load_json(_legacy_auth_path(slug), default={})
    if env_id in legacy:
        return {"auth": legacy[env_id]}

    return {}


def get(project_id, env_id):
    slug = _require_project_and_env(project_id, env_id)
    env_settings = _load_env_settings(slug, env_id)
    auth = {**_AUTH_DEFAULTS, **env_settings.get("auth", {})}
    return {**env_settings, "auth": auth}


def save(project_id, env_id, settings):
    slug = _require_project_and_env(project_id, env_id)

    all_settings = load_json(_settings_path(slug), default={})
    current = _load_env_settings(slug, env_id)

    # Merge top-level sections so unknown future keys are preserved
    merged = {**current, **settings}

    # Validate and normalise the auth section if present
    if "auth" in merged:
        auth = merged["auth"] or {}
        auth_type = (auth.get("auth_type") or "none").strip()
        if auth_type not in VALID_AUTH_TYPES:
            raise BadRequest(f"Invalid auth_type '{auth_type}': must be one of {sorted(VALID_AUTH_TYPES)}")
        merged["auth"] = {
            "auth_type": auth_type,
            "auth_endpoint": (auth.get("auth_endpoint") or "").strip(),
            "request_body_template": auth.get("request_body_template") or _AUTH_DEFAULTS["request_body_template"],
            "token_path": (auth.get("token_path") or "token").strip(),
        }

    all_settings[env_id] = merged
    save_json(_settings_path(slug), all_settings)
    return merged


def _resolve_path(data, dot_path):
    current = data
    for part in dot_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None, False
        current = current[part]
    return current, True


def test_auth(project_id, env_id, auth_config):
    """Fire the configured login request using the first test user. Always returns a result dict."""
    if auth_config.get("auth_type") != "bearer_login":
        return {"success": False, "message": "Auth type is not Bearer Token"}

    try:
        users = list_for_env(project_id, env_id)
    except Exception:
        users = []

    if not users:
        return {"success": False, "message": "No test users configured for this environment. Add one in the Test Users tab first."}

    user = users[0]
    auth_endpoint = (auth_config.get("auth_endpoint") or "").strip()
    if not auth_endpoint:
        return {"success": False, "message": "Auth endpoint is not configured"}

    template = auth_config.get("request_body_template") or _AUTH_DEFAULTS["request_body_template"]
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

    token_path = (auth_config.get("token_path") or "token").strip()
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
