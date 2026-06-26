import glob
import json
import os
import threading
from datetime import datetime, timezone

from app.controllers import BadRequest, NotFound
from app.controllers import environments_controller
from app.controllers.generations_controller import get_generation
from app.controllers.projects_controller import find_project
from app.storage.json_store import data_path, load_json, new_id, save_json
from Utils.logger import logger


def _exec_path(slug, exec_id):
    return data_path(slug, "executions", f"{exec_id}.json")


def _get_execution(slug, exec_id):
    return load_json(_exec_path(slug, exec_id), default=None)


def _save_execution(slug, exc):
    save_json(_exec_path(slug, exc["id"]), exc)


def _list_executions(slug):
    exec_dir = data_path(slug, "executions")
    if not os.path.isdir(exec_dir):
        return []
    execs = [load_json(f) for f in glob.glob(os.path.join(exec_dir, "*.json"))]
    return sorted(execs, key=lambda x: x.get("started_at", ""), reverse=True)


def _run_execution(slug, exec_id, output_dir, testcases_path, base_url_override=None, environment_name=None):
    exc = _get_execution(slug, exec_id)
    exc["status"] = "RUNNING"
    _save_execution(slug, exc)

    logger.info("Execution %s started, output_dir=%s testcases_path=%s", exec_id, output_dir, testcases_path)

    try:
        from execution.execution_runner import ExecutionRunner

        report_paths = ExecutionRunner.execute(
            output_dir, testcases_path,
            base_url_override=base_url_override,
            environment_name=environment_name,
        )

        with open(report_paths["latest_json_report"], encoding="utf-8") as f:
            results = json.load(f)

        total = len(results)
        passed = sum(1 for r in results if r.get("status") == "PASS")
        skipped = sum(1 for r in results if r.get("status") == "SKIPPED")
        failed = total - passed - skipped
        rated = total - skipped

        exc["status"] = "COMPLETED"
        exc["completed_at"] = datetime.now(timezone.utc).isoformat()
        exc["report_html"] = os.path.abspath(report_paths["history_html_report"])
        exc["report_json"] = os.path.abspath(report_paths["history_json_report"])
        exc["summary"] = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "success_rate": round((passed / rated) * 100, 2) if rated > 0 else 0,
        }

        logger.info(
            "Execution %s completed: total=%s passed=%s failed=%s skipped=%s",
            exec_id, total, passed, failed, skipped,
        )

    except Exception as e:
        exc["status"] = "FAILED"
        exc["error"] = str(e)
        exc["completed_at"] = datetime.now(timezone.utc).isoformat()

        logger.error("Execution %s failed: %s", exec_id, e, exc_info=e)

    _save_execution(slug, exc)


def execute(project_id, gen_id, environment_id=None):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")

    slug = p["slug"]
    gen = get_generation(slug, gen_id)
    if gen is None:
        raise NotFound("generation not found")

    if gen["status"] != "APPROVED":
        raise BadRequest("generation must be APPROVED before executing")

    envs = environments_controller.list_all(project_id)
    if environment_id:
        env = next((e for e in envs if e["id"] == environment_id), None)
        if env is None:
            raise BadRequest("environment not found")
    else:
        env = envs[0] if envs else None

    exec_id = new_id()
    now = datetime.now(timezone.utc).isoformat()
    exc = {
        "id": exec_id,
        "project_id": project_id,
        "generation_id": gen_id,
        "status": "PENDING",
        "started_at": now,
        "completed_at": None,
        "report_html": None,
        "report_json": None,
        "summary": None,
        "error": None,
        "environment_id": env["id"] if env else None,
        "environment_name": env["name"] if env else None,
        "base_url": env["url"] if env else None,
    }
    _save_execution(slug, exc)

    logger.info("Execution %s queued for project_id=%s generation_id=%s", exec_id, project_id, gen_id)

    threading.Thread(
        target=_run_execution,
        args=(slug, exec_id, gen["output_dir"], gen["testcases_path"],
              env["url"] if env else None, env["name"] if env else None),
        daemon=True,
    ).start()

    return {"execution_id": exec_id, "status": "PENDING"}


def list_all(project_id):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")
    return _list_executions(p["slug"])


def get(project_id, exec_id):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")

    exc = _get_execution(p["slug"], exec_id)
    if exc is None:
        raise NotFound("execution not found")

    return exc


def get_report_path(project_id, exec_id):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")

    exc = _get_execution(p["slug"], exec_id)
    if exc is None:
        raise NotFound("execution not found")

    html_path = exc.get("report_html")
    if not html_path or not os.path.isfile(html_path):
        raise NotFound("report not available yet")

    return html_path


def get_results(project_id, exec_id):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")

    exc = _get_execution(p["slug"], exec_id)
    if exc is None:
        raise NotFound("execution not found")

    json_path = exc.get("report_json")
    if not json_path or not os.path.isfile(json_path):
        raise NotFound("results not available yet")

    with open(json_path, encoding="utf-8") as f:
        return json.load(f)
