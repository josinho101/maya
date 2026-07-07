import os
import re
import shutil
from datetime import datetime, timezone

from app.controllers import BadRequest, NotFound
from app.storage.json_store import BASE_DIR, data_path, load_json, new_id, save_json
from configs.settings import PATHS
from Utils.logger import logger

PROJECTS_FILE = data_path("projects.json")


def _slugify(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _all_projects():
    return load_json(PROJECTS_FILE, default=[])


def _save_projects(projects):
    save_json(PROJECTS_FILE, projects)


def find_project(project_id):
    for p in _all_projects():
        if p["id"] == project_id:
            return p
    return None


def list_all():
    return _all_projects()


def create(name, description=""):
    name = (name or "").strip()
    if not name:
        raise BadRequest("name is required")

    slug = _slugify(name)
    project_id = new_id()
    now = datetime.now(timezone.utc).isoformat()

    project = {
        "id": project_id,
        "name": name,
        "slug": slug,
        "description": description,
        "created_at": now,
        "updated_at": now,
    }

    projects = _all_projects()
    projects.append(project)
    _save_projects(projects)
    save_json(data_path(slug, "meta.json"), project)

    logger.info("Project created id=%s slug=%s name=%s", project_id, slug, name)

    return project


def get(project_id):
    p = find_project(project_id)
    if not p:
        raise NotFound("not found")

    slug = p["slug"]

    gen_dir = data_path(slug, "generations")
    gen_count = len(os.listdir(gen_dir)) if os.path.isdir(gen_dir) else 0

    exec_dir = data_path(slug, "executions")
    exec_count = len(os.listdir(exec_dir)) if os.path.isdir(exec_dir) else 0

    swagger_meta = load_json(data_path(slug, "swagger", "meta.json"), default=None)

    if swagger_meta:
        parsed_json_path = swagger_meta.get("parsed_json_path", "")
        if parsed_json_path:
            full_path = (
                parsed_json_path
                if os.path.isabs(parsed_json_path)
                else os.path.join(BASE_DIR, parsed_json_path)
            )
            parsed_api = load_json(full_path, default={})
            swagger_meta = {
                **swagger_meta,
                "base_url": parsed_api.get("project", {}).get("base_url"),
            }

    return {
        **p,
        "generation_count": gen_count,
        "execution_count": exec_count,
        "swagger": swagger_meta,
    }


def update(project_id, name=None, description=None):
    projects = _all_projects()

    for i, p in enumerate(projects):
        if p["id"] == project_id:
            p["name"] = ((name or p["name"]) or p["name"]).strip()
            if description is not None:
                p["description"] = description
            p["updated_at"] = datetime.now(timezone.utc).isoformat()
            projects[i] = p
            _save_projects(projects)
            # Preserve extra fields in meta.json (e.g. current_generation_id)
            existing_meta = load_json(data_path(p["slug"], "meta.json"), default={})
            save_json(data_path(p["slug"], "meta.json"), {**existing_meta, **p})
            logger.info("Project updated id=%s slug=%s", project_id, p["slug"])
            return p

    raise NotFound("not found")


def delete(project_id):
    projects = _all_projects()
    found = next((p for p in projects if p["id"] == project_id), None)
    if not found:
        raise NotFound("not found")

    slug = found["slug"]
    _save_projects([p for p in projects if p["id"] != project_id])

    for folder in [PATHS["data"], PATHS["output"], PATHS["execution_results"], "uploads"]:
        path = os.path.join(BASE_DIR, folder, slug)
        if os.path.isdir(path):
            shutil.rmtree(path)

    logger.warning("Project deleted id=%s slug=%s (data directories removed)", project_id, slug)

    return {"deleted": project_id}
