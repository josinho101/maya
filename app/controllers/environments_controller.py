import json
from urllib.parse import urlparse

from app.controllers import BadRequest, NotFound
from app.controllers.projects_controller import find_project
from app.storage.json_store import data_path, load_json, new_id, save_json


def _env_path(slug):
    return data_path(slug, "environments.json")


def _load(slug):
    return load_json(_env_path(slug), default=[])


def _save(slug, envs):
    save_json(_env_path(slug), envs)


def sync_from_swagger(slug, servers):
    """
    Adds any server URL not already present, tagged source='swagger'.
    Existing environments (matched by URL) are left untouched.
    Returns (full_list, added_any).
    """
    existing = _load(slug)
    existing_urls = {e["url"] for e in existing}
    added = False

    for s in servers:
        url = s.get("url", "")
        if url and url not in existing_urls:
            existing.append({
                "id": new_id(),
                "name": s.get("description") or f"Server {len(existing) + 1}",
                "url": url,
                "source": "swagger",
            })
            existing_urls.add(url)
            added = True

    if added:
        _save(slug, existing)

    return existing, added


def list_all(project_id):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")

    slug = p["slug"]
    envs = _load(slug)

    if not envs:
        # Backfill for projects that uploaded their swagger before this
        # feature existed - build the list from the already-parsed spec
        # instead of requiring a migration step.
        meta = load_json(data_path(slug, "swagger", "meta.json"), default=None)
        if meta and meta.get("parsed_json_path"):
            with open(meta["parsed_json_path"], encoding="utf-8") as f:
                servers = json.load(f).get("project", {}).get("servers", [])
            envs, _ = sync_from_swagger(slug, servers)

    return envs


def create_manual(project_id, name, url):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")

    name = (name or "").strip()
    url = (url or "").strip()
    if not name or not url:
        raise BadRequest("name and url are required")

    parsed = urlparse(url)
    if not (parsed.scheme and parsed.netloc):
        raise BadRequest("invalid url")

    slug = p["slug"]
    envs = _load(slug)
    envs.append({"id": new_id(), "name": name, "url": url, "source": "manual"})
    _save(slug, envs)

    return envs


def delete(project_id, env_id):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")

    slug = p["slug"]
    envs = _load(slug)
    env = next((e for e in envs if e["id"] == env_id), None)
    if env is None:
        raise NotFound("environment not found")
    if env.get("source") != "manual":
        raise BadRequest("only manually-added environments can be deleted")

    envs = [e for e in envs if e["id"] != env_id]
    _save(slug, envs)

    return envs


def rename_many(project_id, items):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")

    slug = p["slug"]
    envs = _load(slug)
    by_id = {e["id"]: e for e in envs}

    for item in items or []:
        env = by_id.get(item.get("id"))
        name = (item.get("name") or "").strip()
        if env and name:
            env["name"] = name
        # URL stays locked for swagger-sourced entries; manual entries could
        # accept a url edit too, but that's not requested for this round.

    _save(slug, envs)

    return envs
