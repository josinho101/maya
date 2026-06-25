import time

from flask import g, request

from app.middleware.auth import get_current_user
from Utils.logger import api_logger

SENSITIVE_FIELDS = {"password"}


def _current_username():
    user = get_current_user()
    return user.get("username") if user else "anonymous"


def _safe_body():
    if not request.is_json:
        return None
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return body
    return {k: ("***" if k in SENSITIVE_FIELDS else v) for k, v in body.items()}


def register_request_logging(app):
    @app.before_request
    def _log_request():
        if not request.path.startswith("/api"):
            return
        g._log_start = time.perf_counter()
        api_logger.info(
            "REQUEST %s %s | user=%s | query=%s | body=%s",
            request.method, request.path, _current_username(),
            dict(request.args), _safe_body(),
        )

    @app.after_request
    def _log_response(response):
        if not request.path.startswith("/api"):
            return response
        start = g.get("_log_start")
        duration_ms = (time.perf_counter() - start) * 1000 if start else -1
        api_logger.info(
            "RESPONSE %s %s | status=%s | duration_ms=%.2f",
            request.method, request.path, response.status_code, duration_ms,
        )
        return response

    @app.teardown_request
    def _log_exception(exc):
        if exc is not None and request.path.startswith("/api"):
            api_logger.error(
                "UNHANDLED EXCEPTION %s %s | %s",
                request.method, request.path, exc, exc_info=exc,
            )
