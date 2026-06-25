import json
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

from werkzeug.utils import secure_filename

from app.controllers import BadRequest, NotFound, ServerError
from app.controllers.projects_controller import find_project
from app.storage.json_store import data_path, ensure_dir, load_json, save_json

ALLOWED_EXTENSIONS = {".yaml", ".yml", ".json"}


def upload(project_id, file):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")

    if file is None:
        raise BadRequest("no file provided")

    filename = secure_filename(file.filename or "")
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise BadRequest("only .yaml, .yml, .json files are allowed")

    slug = p["slug"]
    swagger_dir = data_path(slug, "swagger")
    ensure_dir(swagger_dir)

    file_path = os.path.join(swagger_dir, filename)
    file.save(file_path)

    return _parse_and_save_meta(slug, file_path, filename)


def import_from_url(project_id, url):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")

    url = (url or "").strip()
    if not url:
        raise BadRequest("url is required")

    try:
        from Parser.Utils.source_loader import SourceLoader
        content = SourceLoader.load(url)
    except RuntimeError as e:
        raise BadRequest(str(e))

    url_path = urlparse(url).path
    url_tail = os.path.basename(url_path)
    if not url_tail or os.path.splitext(url_tail)[1].lower() not in ALLOWED_EXTENSIONS:
        url_tail = "swagger_from_url.json"
    filename = secure_filename(url_tail)

    slug = p["slug"]
    swagger_dir = data_path(slug, "swagger")
    ensure_dir(swagger_dir)

    file_path = os.path.join(swagger_dir, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(content, f)

    meta = _parse_and_save_meta(slug, file_path, filename)
    meta["source_url"] = url
    save_json(data_path(slug, "swagger", "meta.json"), meta)
    return meta


def get(project_id):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")

    meta = load_json(data_path(p["slug"], "swagger", "meta.json"), default=None)
    if meta is None:
        raise NotFound("no swagger uploaded")

    return meta


def _parse_and_save_meta(slug, file_path, filename):
    try:
        from Parser.rest_document_parser import RestDocumentParser

        parser = RestDocumentParser()
        project_path, parsed_json_path = parser.parse(file_path, namespace=slug)

        with open(parsed_json_path, encoding="utf-8") as f:
            parsed = json.load(f)
        endpoint_count = len(parsed.get("apis", []))

        now = datetime.now(timezone.utc).isoformat()
        meta = {
            "filename": filename,
            "file_path": file_path,
            "uploaded_at": now,
            "parsed_at": now,
            "endpoint_count": endpoint_count,
            "output_dir": project_path,
            "parsed_json_path": parsed_json_path,
        }
        save_json(data_path(slug, "swagger", "meta.json"), meta)
        return meta

    except Exception as e:
        raise ServerError(f"parse failed: {str(e)}")
