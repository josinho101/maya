import glob
import json
import os
import threading
from datetime import datetime, timezone

from app.controllers import BadRequest, NotFound
from app.controllers.projects_controller import find_project
from app.storage.json_store import data_path, load_json, new_id, save_json
from Utils.logger import logger


def _gen_path(slug, gen_id):
    return data_path(slug, "generations", f"{gen_id}.json")


def get_generation(slug, gen_id):
    return load_json(_gen_path(slug, gen_id), default=None)


def _save_generation(slug, gen):
    save_json(_gen_path(slug, gen["id"]), gen)


def _list_generations(slug):
    gen_dir = data_path(slug, "generations")
    if not os.path.isdir(gen_dir):
        return []
    gens = [load_json(f) for f in glob.glob(os.path.join(gen_dir, "*.json"))]
    return sorted(gens, key=lambda x: x.get("created_at", ""), reverse=True)


def _run_generation(slug, gen_id, parsed_json_path, output_dir, existing_testcases_path, endpoints_to_regenerate):
    gen = get_generation(slug, gen_id)
    gen["status"] = "GENERATING"
    gen["progress"] = None
    _save_generation(slug, gen)

    logger.info("Generation %s started for project slug=%s output_dir=%s", gen_id, slug, output_dir)

    def _progress(completed, total, endpoint, method):
        g = get_generation(slug, gen_id)
        g["progress"] = {"completed": completed, "total": total, "current": f"{method} {endpoint}"}
        _save_generation(slug, g)

    try:
        from llm.core.llm_client import LLMClient
        from testcase_generator.testcase_generator import TestcaseGenerator
        from storage.testcase_storage import TestCaseStorage

        if not endpoints_to_regenerate:
            TestCaseStorage.delete(output_dir)
        elif existing_testcases_path:
            TestCaseStorage.remove_endpoints(existing_testcases_path, endpoints_to_regenerate)

        llm = LLMClient.get_llm_client()
        generator = TestcaseGenerator(llm)
        result = generator.generate_test_cases(
            parsed_json_path,
            existing_testcases_path,
            endpoints_to_regenerate=endpoints_to_regenerate,
            progress_callback=_progress,
        )
        saved_file = TestCaseStorage.save(output_dir, result)

        gen = get_generation(slug, gen_id)
        gen["status"] = "REVIEW"
        gen["completed_at"] = datetime.now(timezone.utc).isoformat()
        gen["testcases_path"] = saved_file
        gen["output_dir"] = output_dir

        logger.info("Generation %s completed, testcases saved to %s", gen_id, saved_file)

    except Exception as e:
        gen = get_generation(slug, gen_id)
        gen["status"] = "FAILED"
        gen["error"] = str(e)
        gen["completed_at"] = datetime.now(timezone.utc).isoformat()

        logger.error("Generation %s failed: %s", gen_id, e, exc_info=e)

    _save_generation(slug, gen)


def trigger(project_id, endpoints_to_regenerate=None):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")

    slug = p["slug"]
    swagger_meta = load_json(data_path(slug, "swagger", "meta.json"), default=None)
    if not swagger_meta:
        raise BadRequest("upload and parse a swagger file first")

    output_dir = swagger_meta["output_dir"]
    parsed_json_path = swagger_meta["parsed_json_path"]

    from storage.testcase_storage import TestCaseStorage
    if not endpoints_to_regenerate:
        existing = None
    else:
        existing = TestCaseStorage.get_existing_testcases(output_dir)

    gen_id = new_id()
    now = datetime.now(timezone.utc).isoformat()
    gen = {
        "id": gen_id,
        "project_id": project_id,
        "status": "PENDING",
        "created_at": now,
        "completed_at": None,
        "error": None,
        "progress": None,
        "testcases_path": None,
        "output_dir": output_dir,
    }
    _save_generation(slug, gen)

    logger.info("Generation %s queued for project_id=%s", gen_id, project_id)

    threading.Thread(
        target=_run_generation,
        args=(slug, gen_id, parsed_json_path, output_dir, existing, endpoints_to_regenerate),
        daemon=True,
    ).start()

    return {"generation_id": gen_id, "status": "PENDING"}


def list_all(project_id):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")
    return _list_generations(p["slug"])


def get(project_id, gen_id):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")

    gen = get_generation(p["slug"], gen_id)
    if gen is None:
        raise NotFound("generation not found")

    if gen["status"] in ("REVIEW", "APPROVED") and gen.get("testcases_path"):
        try:
            with open(gen["testcases_path"], encoding="utf-8") as f:
                gen["testcases"] = json.load(f)
        except Exception:
            gen["testcases"] = None

    return gen


def edit_testcase(project_id, gen_id, tc_id, updated_tc):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")

    gen = get_generation(p["slug"], gen_id)
    if gen is None:
        raise NotFound("generation not found")

    if not gen.get("testcases_path"):
        raise BadRequest("no test cases available")

    if not updated_tc:
        raise BadRequest("request body required")

    with open(gen["testcases_path"], encoding="utf-8") as f:
        data = json.load(f)

    found = False
    for result in data.get("results", []):
        for i, tc in enumerate(result.get("test_cases", [])):
            if tc.get("tc_id") == tc_id:
                result["test_cases"][i] = updated_tc
                found = True
                break
        if found:
            break

    if not found:
        raise NotFound(f"tc_id '{tc_id}' not found")

    from storage.testcase_storage import TestCaseStorage
    TestCaseStorage.save(gen["output_dir"], data)

    return updated_tc


def delete_testcase(project_id, gen_id, tc_id):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")

    gen = get_generation(p["slug"], gen_id)
    if gen is None:
        raise NotFound("generation not found")

    if not gen.get("testcases_path"):
        raise BadRequest("no test cases available")

    with open(gen["testcases_path"], encoding="utf-8") as f:
        data = json.load(f)

    found = False
    for result in data.get("results", []):
        before = len(result.get("test_cases", []))
        result["test_cases"] = [tc for tc in result.get("test_cases", []) if tc.get("tc_id") != tc_id]
        if len(result["test_cases"]) < before:
            found = True
            break

    if not found:
        raise NotFound(f"tc_id '{tc_id}' not found")

    from storage.testcase_storage import TestCaseStorage
    TestCaseStorage.save(gen["output_dir"], data)

    return {"deleted": tc_id}


def approve(project_id, gen_id):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")

    gen = get_generation(p["slug"], gen_id)
    if gen is None:
        raise NotFound("generation not found")

    if gen["status"] != "REVIEW":
        raise BadRequest(f"cannot approve from status '{gen['status']}'")

    gen["status"] = "APPROVED"
    _save_generation(p["slug"], gen)

    return {"status": "APPROVED", "generation_id": gen_id}
