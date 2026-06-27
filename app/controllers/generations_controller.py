import glob
import json
import os
import threading
import uuid
from datetime import datetime, timezone

from werkzeug.utils import secure_filename

from app.controllers import BadRequest, NotFound
from app.controllers.projects_controller import find_project
from app.storage.json_store import data_path, load_json, new_id, save_json
from testcase_generator.testcase_validator import validate_testcase, demote_duplicate_lifecycle_role
from testcase_generator.testcaseIdGenerator import TCIDGenerator
from testcase_generator.sample_builder import build_sample_testcase
from Utils.logger import logger


def _gen_path(slug, gen_id):
    return data_path(slug, "generations", f"{gen_id}.json")


def get_generation(slug, gen_id):
    return load_json(_gen_path(slug, gen_id), default=None)


def _save_generation(slug, gen):
    save_json(_gen_path(slug, gen["id"]), gen)


def _get_project_and_generation(project_id, gen_id):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")

    gen = get_generation(p["slug"], gen_id)
    if gen is None:
        raise NotFound("generation not found")

    return p, gen


def load_testcases_data(gen):
    if not gen.get("testcases_path"):
        raise BadRequest("no test cases available")

    with open(gen["testcases_path"], encoding="utf-8") as f:
        return json.load(f)


def _save_testcases_data(gen, data):
    from storage.testcase_storage import TestCaseStorage
    TestCaseStorage.save(gen["output_dir"], data)


def find_result(data, endpoint, method):
    for idx, result in enumerate(data.get("results", [])):
        if result.get("endpoint") == endpoint and result.get("method", "").upper() == method.upper():
            return idx, result
    return None, None


def get_swagger_meta(slug):
    swagger_meta = load_json(data_path(slug, "swagger", "meta.json"), default=None)
    if not swagger_meta:
        raise BadRequest("upload and parse a swagger file first")
    return swagger_meta


def find_api(parsed_json_path, endpoint, method):
    with open(parsed_json_path, encoding="utf-8") as f:
        api_input = json.load(f)

    for api in api_input.get("apis", []):
        details = api.get("api_details", {})
        if details.get("endpoint") == endpoint and details.get("method", "").upper() == method.upper():
            return api

    return None


def _backfill_provenance(data):
    """
    Test case files written before source/needs_review existed have neither
    key. Treat them as already-reviewed system output rather than forcing old
    generations to suddenly need re-review.
    """
    for result in data.get("results", []):
        for tc in result.get("test_cases", []):
            tc.setdefault("source", "system")
            tc.setdefault("needs_review", False)
    return data


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

    def _steps_progress(completed, total, tc_id):
        g = get_generation(slug, gen_id)
        g["progress"] = {"completed": completed, "total": total, "current": tc_id}
        _save_generation(slug, g)

    try:
        from llm.core.llm_client import LLMClient
        from testcase_generator.testcase_generator import TestcaseGenerator
        from testcase_generator.step_generator import generate_steps_for_all
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
            stop_check=lambda: get_generation(slug, gen_id).get("stop_requested", False),
        )

        gen = get_generation(slug, gen_id)
        # Only narrate steps if scenario generation wasn't stopped - skip
        # straight to saving the partial results otherwise, same as before
        # this second phase existed.
        if not gen.get("stop_requested", False):
            gen["status"] = "SCENARIOS_READY"
            _save_generation(slug, gen)

            gen["status"] = "GENERATING_STEPS"
            gen["progress"] = None
            _save_generation(slug, gen)

            result = generate_steps_for_all(
                llm, result,
                progress_callback=_steps_progress,
                stop_check=lambda: get_generation(slug, gen_id).get("stop_requested", False),
            )

        # testcases_path is only set below, after both phases - the
        # generation doesn't reach REVIEW, and nothing is exposed to the UI,
        # until step narration has also finished.
        saved_file = TestCaseStorage.save(output_dir, result)

        gen = get_generation(slug, gen_id)
        # stop_requested may have been set while the last endpoint's LLM call
        # or the last test case's step-narration call was already in flight -
        # re-check now rather than trusting an earlier snapshot.
        stopped = gen.get("stop_requested", False)
        gen["status"] = "STOPPED" if stopped else "REVIEW"
        gen["completed_at"] = datetime.now(timezone.utc).isoformat()
        gen["testcases_path"] = saved_file
        gen["output_dir"] = output_dir

        if stopped:
            logger.info("Generation %s stopped by request, partial results saved to %s", gen_id, saved_file)
        else:
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
    swagger_meta = get_swagger_meta(slug)

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
    p, gen = _get_project_and_generation(project_id, gen_id)

    if gen["status"] in ("REVIEW", "APPROVED") and gen.get("testcases_path"):
        try:
            with open(gen["testcases_path"], encoding="utf-8") as f:
                gen["testcases"] = _backfill_provenance(json.load(f))
        except Exception:
            gen["testcases"] = None

    return gen


def edit_testcase(project_id, gen_id, tc_id, updated_tc):
    p, gen = _get_project_and_generation(project_id, gen_id)

    if not updated_tc:
        raise BadRequest("request body required")

    data = load_testcases_data(gen)

    found = False
    for result in data.get("results", []):
        for i, tc in enumerate(result.get("test_cases", [])):
            if tc.get("tc_id") == tc_id:
                # A human just wrote this content, so it's already reviewed -
                # only LLM output needs the review queue. tc_id is pinned to
                # the URL param so the request body can't accidentally move
                # the edit elsewhere.
                updated_tc = {**updated_tc, "tc_id": tc_id, "needs_review": False}
                result["test_cases"][i] = updated_tc
                found = True
                break
        if found:
            break

    if not found:
        raise NotFound(f"tc_id '{tc_id}' not found")

    _save_testcases_data(gen, data)

    still_pending = any(
        tc.get("needs_review")
        for result in data.get("results", [])
        for tc in result.get("test_cases", [])
    )
    if gen["status"] == "REVIEW" and not still_pending:
        gen["status"] = "APPROVED"
        _save_generation(p["slug"], gen)

    logger.info("Test case %s edited (project=%s gen=%s)", tc_id, project_id, gen_id)

    return updated_tc


def approve_testcase(project_id, gen_id, tc_id):
    p, gen = _get_project_and_generation(project_id, gen_id)

    data = load_testcases_data(gen)

    found = False
    for result in data.get("results", []):
        for tc in result.get("test_cases", []):
            if tc.get("tc_id") == tc_id:
                tc["needs_review"] = False
                found = True
                break
        if found:
            break

    if not found:
        raise NotFound(f"tc_id '{tc_id}' not found")

    _save_testcases_data(gen, data)

    still_pending = any(
        tc.get("needs_review")
        for result in data.get("results", [])
        for tc in result.get("test_cases", [])
    )
    if gen["status"] == "REVIEW" and not still_pending:
        gen["status"] = "APPROVED"
        _save_generation(p["slug"], gen)

    logger.info("Test case %s approved (project=%s gen=%s)", tc_id, project_id, gen_id)

    return {"tc_id": tc_id, "needs_review": False, "generation_status": gen["status"]}


def delete_testcase(project_id, gen_id, tc_id):
    p, gen = _get_project_and_generation(project_id, gen_id)

    data = load_testcases_data(gen)

    found = False
    for result in data.get("results", []):
        before = len(result.get("test_cases", []))
        result["test_cases"] = [tc for tc in result.get("test_cases", []) if tc.get("tc_id") != tc_id]
        if len(result["test_cases"]) < before:
            found = True
            break

    if not found:
        raise NotFound(f"tc_id '{tc_id}' not found")

    _save_testcases_data(gen, data)

    logger.info("Test case %s deleted (project=%s gen=%s)", tc_id, project_id, gen_id)

    return {"deleted": tc_id}


def add_testcase(project_id, gen_id, endpoint, method, new_tc, needs_review=True):
    p, gen = _get_project_and_generation(project_id, gen_id)

    if not new_tc:
        raise BadRequest("request body required")

    if not endpoint or not method:
        raise BadRequest("endpoint and method are required")

    try:
        validate_testcase(new_tc)
    except ValueError as e:
        logger.warning(
            "add_testcase rejected for project=%s gen=%s endpoint='%s %s': %s",
            project_id, gen_id, method, endpoint, e,
        )
        raise BadRequest(str(e))

    data = load_testcases_data(gen)

    idx, result = find_result(data, endpoint, method)
    if result is None:
        raise NotFound(f"endpoint '{method} {endpoint}' not found in this generation")

    existing_test_cases = result.setdefault("test_cases", [])

    demote_duplicate_lifecycle_role(new_tc, existing_test_cases)

    tc_id = TCIDGenerator.next_id(existing_test_cases, idx + 1)

    saved_tc = {**new_tc, "tc_id": tc_id, "source": "manual", "needs_review": needs_review}
    existing_test_cases.append(saved_tc)

    _save_testcases_data(gen, data)

    logger.info(
        "Test case %s added manually to '%s %s' (project=%s gen=%s)",
        tc_id, method, endpoint, project_id, gen_id,
    )

    return saved_tc


def get_sample_testcase(project_id, gen_id, endpoint, method):
    p, gen = _get_project_and_generation(project_id, gen_id)

    if not endpoint or not method:
        raise BadRequest("endpoint and method are required")

    swagger_meta = get_swagger_meta(p["slug"])
    api = find_api(swagger_meta["parsed_json_path"], endpoint, method)
    if api is None:
        raise NotFound(f"endpoint '{method} {endpoint}' not found in this project's API spec")

    sample, file_fields = build_sample_testcase(api.get("api_details", {}))

    return {
        "sample": sample,
        "file_fields": file_fields,
        "accepts_file": bool(file_fields),
    }


def upload_testcase_file(project_id, gen_id, file_storage):
    p, gen = _get_project_and_generation(project_id, gen_id)

    if not gen.get("output_dir"):
        raise BadRequest("no output directory available for this generation")

    if not file_storage or not file_storage.filename:
        raise BadRequest("file is required")

    upload_dir = os.path.join(gen["output_dir"], "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    safe_name = secure_filename(file_storage.filename)
    if not safe_name:
        raise BadRequest("invalid filename")

    stored_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    stored_path = os.path.abspath(os.path.join(upload_dir, stored_name))

    file_storage.save(stored_path)

    logger.info(
        "File uploaded for project=%s gen=%s -> %s", project_id, gen_id, stored_path
    )

    return {"path": stored_path}


def list_testcase_files(project_id, gen_id):
    p, gen = _get_project_and_generation(project_id, gen_id)

    if not gen.get("output_dir"):
        return []

    upload_dir = os.path.join(gen["output_dir"], "uploads")
    if not os.path.isdir(upload_dir):
        return []

    files = []
    for stored_name in os.listdir(upload_dir):
        stored_path = os.path.abspath(os.path.join(upload_dir, stored_name))
        if not os.path.isfile(stored_path):
            continue
        # Stored as "{8 hex chars}_{original filename}" (see upload_testcase_file).
        display_name = stored_name[9:] if len(stored_name) > 9 and stored_name[8] == "_" else stored_name
        stat = os.stat(stored_path)
        files.append({
            "path": stored_path,
            "name": display_name,
            "size": stat.st_size,
            "uploaded_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        })

    files.sort(key=lambda f: f["uploaded_at"], reverse=True)
    return files


def request_stop_generation(project_id, gen_id):
    p, gen = _get_project_and_generation(project_id, gen_id)

    if gen["status"] not in ("PENDING", "GENERATING", "SCENARIOS_READY", "GENERATING_STEPS"):
        raise BadRequest(f"cannot stop generation in status '{gen['status']}'")

    gen["stop_requested"] = True
    _save_generation(p["slug"], gen)

    logger.info("Stop requested for generation %s (project=%s)", gen_id, project_id)

    return gen


def approve(project_id, gen_id):
    p, gen = _get_project_and_generation(project_id, gen_id)

    if gen["status"] not in ("REVIEW", "APPROVED"):
        raise BadRequest(f"cannot approve from status '{gen['status']}'")

    data = load_testcases_data(gen)
    for result in data.get("results", []):
        for tc in result.get("test_cases", []):
            tc["needs_review"] = False
    _save_testcases_data(gen, data)

    gen["status"] = "APPROVED"
    _save_generation(p["slug"], gen)

    logger.info("Generation %s approved (project=%s)", gen_id, project_id)

    return {"status": "APPROVED", "generation_id": gen_id}
