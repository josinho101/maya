"""Minimal synchronous run-trigger + report-read API (F7-090), per plan.md §5.f
but intentionally the simple precursor to that full async contract — F12/F13 add
job-queue dispatch later without changing `RunOrchestrator`'s signature."""

from __future__ import annotations

from fastapi import APIRouter, Request

from maya.managers.project_manager import ProjectManager
from maya.runners.run_orchestrator import RunOrchestrator
from maya.storage.models import RunSummary

router = APIRouter(tags=["runs"])


class RunNotFoundError(LookupError):
    pass


def get_project_manager(request: Request) -> ProjectManager:
    return request.app.state.project_manager


@router.post("/api/v1/projects/{project_id}/runs")
def trigger_run(project_id: str, environment: str, request: Request) -> RunSummary:
    root_dir = get_project_manager(request).root_dir
    return RunOrchestrator(root_dir).run(project_id, environment)


@router.get("/api/v1/runs/{run_id}")
def get_run(run_id: str, request: Request) -> RunSummary:
    root_dir = get_project_manager(request).root_dir
    for run_summary_path in root_dir.glob(f"projects/*/environments/*/runs/{run_id}/run_summary.json"):
        return RunSummary.model_validate_json(run_summary_path.read_bytes())
    raise RunNotFoundError(f"run {run_id!r} not found")
