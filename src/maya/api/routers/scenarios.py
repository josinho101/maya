"""Scenario submission API (F10-010), mirroring `runs.py`'s F7-090 synchronous
precursor pattern: POST kicks off the full `ScenarioInterpreter` run
synchronously and returns the resulting `ScenarioSession`; GET re-fetches it
by id (F10-060's status-polling read endpoint)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from maya.managers.project_manager import ProjectManager
from maya.runners.scenario_runner import run_scenario
from maya.storage.models import ScenarioSession
from maya.storage.scenario_session_store import ScenarioSessionStore

router = APIRouter(prefix="/api/v1/projects", tags=["scenarios"])


def get_project_manager(request: Request) -> ProjectManager:
    return request.app.state.project_manager


class SubmitScenarioRequest(BaseModel):
    text: str
    environment_id: str


@router.post("/{project_id}/scenarios")
def submit_scenario(
    project_id: str, body: SubmitScenarioRequest, request: Request
) -> ScenarioSession:
    root_dir = get_project_manager(request).root_dir
    return run_scenario(root_dir, project_id, body.environment_id, body.text)


@router.get("/{project_id}/scenarios/{session_id}")
def get_scenario_session(
    project_id: str, session_id: str, request: Request
) -> ScenarioSession:
    manager = get_project_manager(request)
    store = ScenarioSessionStore(manager.project_dir(project_id))
    return store.get(session_id)
