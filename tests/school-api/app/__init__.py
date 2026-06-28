import os
import shutil

from flasgger import Flasgger
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from app import settings


def create_app():
    shutil.rmtree(settings.UPLOADS_DIR, ignore_errors=True)
    os.makedirs(settings.UPLOADS_DIR, exist_ok=True)

    app = Flask(__name__)
    CORS(app)

    app.config["SWAGGER"] = {
        "title": "School API",
        "openapi": "3.0.3",
        "uiversion": 3,
        "specs_route": "/swagger/",
        "specs": [
            {
                "endpoint": "swagger",
                "route": "/swagger.json",
            }
        ],
    }
    Flasgger(app, template={
        "servers": [
            {"url": "http://localhost:8070", "description": "Local"},
        ],
        "components": {
            "securitySchemes": {
                "Bearer": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "JWT token issued by /api/auth/login. Paste only the raw token (Swagger UI adds the 'Bearer ' prefix automatically).",
                }
            }
        },
    })

    from app.routes.auth import bp as auth_bp
    from app.routes.classes import bp as classes_bp
    from app.routes.students import bp as students_bp
    from app.routes.teachers import bp as teachers_bp

    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(classes_bp, url_prefix="/api")
    app.register_blueprint(students_bp, url_prefix="/api")
    app.register_blueprint(teachers_bp, url_prefix="/api")

    from app.controllers import BadRequest, NotFound, ServerError

    @app.errorhandler(NotFound)
    def handle_not_found(e):
        return jsonify({"error": str(e)}), 404

    @app.errorhandler(BadRequest)
    def handle_bad_request(e):
        return jsonify({"error": str(e)}), 400

    @app.errorhandler(ServerError)
    def handle_server_error(e):
        return jsonify({"error": str(e)}), 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        if isinstance(e, HTTPException):
            return e
        return jsonify({"error": "Internal server error"}), 500

    @app.get("/uploads/<filename>")
    def serve_upload(filename):
        return send_from_directory(settings.UPLOADS_DIR, filename)

    return app
