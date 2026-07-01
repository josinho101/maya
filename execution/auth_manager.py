import json

import requests

from Utils.logger import logger


def _resolve_path(data, dot_path):
    current = data
    for part in dot_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


class AuthManager:
    """
    Scoped to one execution run. Fetches and caches bearer tokens per user so
    that the auth endpoint is called at most once per user per run. Call
    clear() after the run to discard cached tokens.
    """

    def __init__(self, auth_config, users_by_id):
        self._config = auth_config or {}
        self._users = users_by_id or {}
        self._token_cache = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_auth_headers(self, requires_auth, auth_schemes, auth_override, env_id, test_user_assignments):
        """
        Returns a dict of headers to merge into the test-case headers before
        the HTTP call is made. Returns {} when no auth header should be added.
        """
        if not requires_auth:
            return {}

        if auth_override == "missing":
            return {}

        if auth_override == "invalid":
            return self._build_auth_header(auth_schemes, "invalid_token")

        # Normal case: acquire real token for the assigned user
        user_id = (test_user_assignments or {}).get(env_id)
        if not user_id:
            logger.warning("No test user assigned for env '%s' — skipping auth header", env_id)
            return {}

        token = self._get_token(user_id)
        if not token:
            return {}

        return self._build_auth_header(auth_schemes, token)

    def clear(self):
        self._token_cache.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_token(self, user_id):
        if user_id in self._token_cache:
            return self._token_cache[user_id]

        user = self._users.get(user_id)
        if not user:
            logger.warning("Test user '%s' not found in user list", user_id)
            return None

        token = self._fetch_token(self._config, user)
        if token:
            self._token_cache[user_id] = token
        return token

    @staticmethod
    def _fetch_token(auth_config, user):
        auth_type = auth_config.get("auth_type", "none")
        if auth_type != "bearer_login":
            return None

        auth_endpoint = (auth_config.get("auth_endpoint") or "").strip()
        if not auth_endpoint:
            logger.warning("Auth endpoint not configured — skipping token fetch")
            return None

        template = auth_config.get("request_body_template") or '{"username": "{{username}}", "password": "{{password}}"}'
        body_str = (
            template
            .replace("{{username}}", user.get("username", ""))
            .replace("{{password}}", user.get("password", ""))
        )

        try:
            body = json.loads(body_str)
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in auth request_body_template: %s", e)
            return None

        try:
            resp = requests.post(auth_endpoint, json=body, timeout=10)
            resp_body = resp.json()
        except requests.exceptions.RequestException as e:
            logger.error("Auth endpoint request failed: %s", e)
            return None
        except ValueError:
            logger.error("Auth endpoint returned non-JSON response")
            return None

        token_path = (auth_config.get("token_path") or "token").strip()
        token = _resolve_path(resp_body, token_path)

        if not token:
            logger.error(
                "Token not found at path '%s' in auth response. Status=%s body=%s",
                token_path, resp.status_code, resp_body,
            )
            return None

        logger.info("Token acquired for user '%s' via '%s'", user.get("username"), auth_endpoint)
        return str(token)

    @staticmethod
    def _build_auth_header(auth_schemes, token):
        for scheme in (auth_schemes or []):
            s_type = scheme.get("type", "")
            s_scheme = scheme.get("scheme", "")
            s_in = scheme.get("in", "")
            param_name = scheme.get("param_name", "")

            if s_type == "http" and s_scheme in ("bearer", "jwt"):
                return {"Authorization": f"Bearer {token}"}
            if s_type == "http" and s_scheme == "basic":
                # bearer_login always produces a bearer token; inject as bearer
                return {"Authorization": f"Bearer {token}"}
            if s_type == "apiKey" and s_in == "header" and param_name:
                return {param_name: token}

        # Default fallback
        return {"Authorization": f"Bearer {token}"}
