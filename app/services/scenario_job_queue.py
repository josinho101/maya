import glob
import os
import queue
import threading
from datetime import datetime, timezone

from app.storage.json_store import data_path, load_json, new_id, save_json
from Utils.logger import logger

_queue = queue.Queue()
_worker_started = False
_start_lock = threading.Lock()


def _job_path(slug, job_id):
    return data_path(slug, "scenario_jobs", f"{job_id}.json")


def get_job(slug, job_id):
    return load_json(_job_path(slug, job_id), default=None)


def _save_job(slug, job):
    save_json(_job_path(slug, job["id"]), job)


def _list_jobs_for_slug(slug):
    job_dir = data_path(slug, "scenario_jobs")
    if not os.path.isdir(job_dir):
        return []
    return [load_json(f) for f in glob.glob(os.path.join(job_dir, "*.json"))]


def list_jobs(slug):
    return sorted(_list_jobs_for_slug(slug), key=lambda j: j.get("created_at", ""), reverse=True)


def create_job(slug, project_id, gen_id, endpoint, method, scenario, files=None):
    job_id = new_id()
    now = datetime.now(timezone.utc).isoformat()
    job = {
        "id": job_id,
        "project_id": project_id,
        "slug": slug,
        "gen_id": gen_id,
        "endpoint": endpoint,
        "method": method,
        "scenario": scenario,
        "files": files or {},
        "status": "QUEUED",
        "stop_requested": False,
        "created_at": now,
        "started_at": None,
        "completed_at": None,
        "tc_id": None,
        "error": None,
    }
    _save_job(slug, job)
    _queue.put((slug, job_id))

    logger.info(
        "Scenario job %s queued for project=%s gen=%s endpoint='%s %s'",
        job_id, project_id, gen_id, method, endpoint,
    )

    return job


def request_stop(slug, job_id):
    job = get_job(slug, job_id)
    if job is None:
        return None

    if job["status"] == "QUEUED":
        # Hasn't started - flip straight to cancelled. queue.Queue has no
        # remove-by-id API, so the worker still dequeues this job id later
        # and skips it once it sees this status (_process_job below).
        job["status"] = "CANCELLED"
        _save_job(slug, job)
    elif job["status"] == "RUNNING":
        # Can't abort the in-flight LLM call from here - flag it so
        # _process_job discards the result instead of saving it once the
        # call returns.
        job["stop_requested"] = True
        _save_job(slug, job)

    return job


def _process_job(slug, job_id):
    # Local imports to avoid a circular import at module load time -
    # generations_controller doesn't import this module, but several other
    # app modules import generations_controller before this one is loaded.
    from app.controllers import generations_controller
    from llm.core.llm_client import LLMClient
    from llm.core.exceptions import LLMResponseError
    from testcase_generator.scenario_generator import generate_from_scenario
    from testcase_generator.step_generator import generate_steps_for_testcase

    job = get_job(slug, job_id)
    if job is None:
        logger.warning("Scenario job %s vanished before it could run", job_id)
        return

    if job["status"] == "CANCELLED":
        logger.info("Scenario job %s was cancelled before it started - skipping", job_id)
        return

    job["status"] = "RUNNING"
    job["started_at"] = datetime.now(timezone.utc).isoformat()
    _save_job(slug, job)

    logger.info(
        "Scenario job %s started (project=%s gen=%s endpoint='%s %s')",
        job_id, job["project_id"], job["gen_id"], job["method"], job["endpoint"],
    )

    try:
        gen = generations_controller.get_generation(slug, job["gen_id"])
        if gen is None:
            raise ValueError("generation not found")

        swagger_meta = generations_controller.get_swagger_meta(slug)
        api = generations_controller.find_api(
            swagger_meta["parsed_json_path"], job["endpoint"], job["method"]
        )
        if api is None:
            raise ValueError(
                f"endpoint '{job['method']} {job['endpoint']}' not found in this project's API spec"
            )

        llm = LLMClient.get_llm_client()
        draft = generate_from_scenario(llm, api, job["scenario"])

        if job.get("files"):
            # A real user-supplied upload always wins over anything the
            # model hallucinated for that field.
            draft["files"] = {**draft.get("files", {}), **job["files"]}

        # The LLM call is the only slow step here - re-check stop_requested
        # now, in case Stop was clicked while it was in flight.
        job = get_job(slug, job_id)
        if job.get("stop_requested"):
            job["status"] = "CANCELLED"
            job["completed_at"] = datetime.now(timezone.utc).isoformat()
            _save_job(slug, job)
            logger.info(
                "Scenario job %s cancelled after its LLM call finished - discarding draft", job_id
            )
            return

        try:
            draft["steps"] = generate_steps_for_testcase(llm, draft, job["endpoint"], job["method"])
        except LLMResponseError as e:
            # The scenario+detail draft above already succeeded - a failure
            # narrating it as steps shouldn't fail the whole job, just leave
            # it without steps.
            draft["steps"] = []
            draft["steps_error"] = str(e)

        saved_tc = generations_controller.add_testcase(
            job["project_id"], job["gen_id"], job["endpoint"], job["method"], draft
        )

        job["status"] = "DONE"
        job["tc_id"] = saved_tc["tc_id"]
        job["completed_at"] = datetime.now(timezone.utc).isoformat()
        _save_job(slug, job)

        logger.info("Scenario job %s completed -> tc_id=%s", job_id, saved_tc["tc_id"])

    except Exception as e:
        job = get_job(slug, job_id)
        job["status"] = "FAILED"
        job["error"] = str(e)
        job["completed_at"] = datetime.now(timezone.utc).isoformat()
        _save_job(slug, job)

        logger.error("Scenario job %s failed: %s", job_id, e, exc_info=e)


def _worker_loop():
    while True:
        slug, job_id = _queue.get()
        try:
            _process_job(slug, job_id)
        except Exception as e:
            logger.error("Scenario job %s crashed outside its own handling: %s", job_id, e, exc_info=e)
        finally:
            _queue.task_done()


def _reconcile_on_startup():
    """
    queue.Queue() is in-memory only, so a server restart loses whatever
    ordering was in it. Re-derive it from disk: re-enqueue every QUEUED job
    in created_at order, and mark any RUNNING job left over from a previous
    process as FAILED - an in-flight LLM call can't be safely resumed, only
    retried via a fresh submission.
    """

    base_dir = data_path()
    if not os.path.isdir(base_dir):
        return

    pending = []

    for slug in os.listdir(base_dir):
        if not os.path.isdir(os.path.join(base_dir, slug)):
            continue

        for job in _list_jobs_for_slug(slug):
            if job.get("status") == "QUEUED":
                pending.append((slug, job))
            elif job.get("status") == "RUNNING":
                job["status"] = "FAILED"
                job["error"] = "interrupted by restart"
                job["completed_at"] = datetime.now(timezone.utc).isoformat()
                _save_job(slug, job)
                logger.warning(
                    "Scenario job %s marked FAILED - was RUNNING during a previous process",
                    job["id"],
                )

    pending.sort(key=lambda item: item[1].get("created_at", ""))

    for slug, job in pending:
        _queue.put((slug, job["id"]))

    if pending:
        logger.info("Re-queued %d scenario job(s) left over from a previous process", len(pending))


def start_worker():
    """
    Starts the single background worker thread (idempotent - safe to call
    more than once, e.g. under a dev-server reloader) and reconciles
    persisted job state from a previous process before taking new work.
    """

    global _worker_started

    with _start_lock:
        if _worker_started:
            return
        _worker_started = True

    _reconcile_on_startup()

    threading.Thread(target=_worker_loop, daemon=True).start()

    logger.info("Scenario job queue worker started")
