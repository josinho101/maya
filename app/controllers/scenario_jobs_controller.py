from app.controllers import BadRequest, NotFound
from app.controllers.projects_controller import find_project
from app.controllers.generations_controller import get_generation, load_testcases_data, find_result
from app.services import scenario_job_queue


def submit_scenario_job(project_id, gen_id, endpoint, method, scenario, files=None):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")

    gen = get_generation(p["slug"], gen_id)
    if gen is None:
        raise NotFound("generation not found")

    if not endpoint or not method:
        raise BadRequest("endpoint and method are required")

    if not scenario or not scenario.strip():
        raise BadRequest("scenario description is required")

    data = load_testcases_data(gen)
    _, result = find_result(data, endpoint, method)
    if result is None:
        raise NotFound(f"endpoint '{method} {endpoint}' not found in this generation")

    return scenario_job_queue.create_job(
        p["slug"], project_id, gen_id, endpoint, method, scenario, files=files
    )


def list_scenario_jobs(project_id):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")

    return scenario_job_queue.list_jobs(p["slug"])


def get_scenario_job(project_id, job_id):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")

    job = scenario_job_queue.get_job(p["slug"], job_id)
    if job is None:
        raise NotFound("job not found")

    return job


def request_stop_scenario_job(project_id, job_id):
    p = find_project(project_id)
    if not p:
        raise NotFound("project not found")

    job = scenario_job_queue.get_job(p["slug"], job_id)
    if job is None:
        raise NotFound("job not found")

    if job["status"] not in ("QUEUED", "RUNNING"):
        raise BadRequest("job already finished")

    return scenario_job_queue.request_stop(p["slug"], job_id)
