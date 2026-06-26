import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from Utils.logger import logger


def create_app():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_folder = os.path.join(base_dir, "frontend", "build")

    app = Flask(__name__, static_folder=static_folder, static_url_path="")
    CORS(app)

    from app.middleware.logging import register_request_logging
    register_request_logging(app)

    from app.routes.auth import bp as auth_bp
    from app.routes.projects import bp as projects_bp
    from app.routes.swagger import bp as swagger_bp
    from app.routes.generations import bp as generations_bp
    from app.routes.executions import bp as executions_bp
    from app.routes.scenario_jobs import bp as scenario_jobs_bp
    from app.routes.environments import bp as environments_bp

    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(projects_bp, url_prefix="/api")
    app.register_blueprint(swagger_bp, url_prefix="/api")
    app.register_blueprint(generations_bp, url_prefix="/api")
    app.register_blueprint(executions_bp, url_prefix="/api")
    app.register_blueprint(scenario_jobs_bp, url_prefix="/api")
    app.register_blueprint(environments_bp, url_prefix="/api")

    from app.services import scenario_job_queue
    scenario_job_queue.start_worker()

    from app.controllers import BadRequest, NotFound, ServerError

    @app.errorhandler(NotFound)
    def handle_not_found(e):
        logger.warning("NotFound: %s", e)
        return jsonify({"error": str(e)}), 404

    @app.errorhandler(BadRequest)
    def handle_bad_request(e):
        logger.warning("BadRequest: %s", e)
        return jsonify({"error": str(e)}), 400

    @app.errorhandler(ServerError)
    def handle_server_error(e):
        logger.error("ServerError: %s", e, exc_info=e)
        return jsonify({"error": str(e)}), 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        if isinstance(e, HTTPException):
            return e
        logger.error("Unhandled exception: %s", e, exc_info=e)
        return jsonify({"error": "Internal server error"}), 500

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_spa(path):
        if path.startswith("api/"):
            return app.make_response(("Not Found", 404))
        if path and os.path.exists(os.path.join(static_folder, path)):
            return send_from_directory(static_folder, path)
        if os.path.exists(os.path.join(static_folder, "index.html")):
            return send_from_directory(static_folder, "index.html")
        return app.make_response(("Frontend not built. Run: cd frontend && npm run build", 200))

    return app
