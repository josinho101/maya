"""F9-110: healing log read + flagged-heal resolution, per plan.md §5.e step 3/4.
`healing-log` is nested under project (mirrors `test_cases.py`'s rationale — both
`TestCaseStore` and the healing-log directories are constructed per-project, there's
no global index). `resolve` and the screenshot endpoint are flat, mirroring
`runs.py::get_run`'s glob-by-globally-unique-id pattern — `heal_id`/`run_id` are
uuid-based and unique across the whole root_dir, so no project_id is needed in the URL."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from maya.managers.project_manager import ProjectManager
from maya.storage.healing_log_store import HealingLogStore
from maya.storage.models import HealingEventLogEntry, LocatorTarget
from maya.storage.test_case_store import TestCaseStore

router = APIRouter(prefix="/api/v1", tags=["healing"])


class HealingNotFoundError(LookupError):
    pass


class ResolveHealingRequest(BaseModel):
    action: Literal["accept", "reject"]


def get_project_manager(request: Request) -> ProjectManager:
    return request.app.state.project_manager


@router.get("/projects/{project_id}/test-cases/{test_case_id}/healing-log")
def get_healing_log(project_id: str, test_case_id: str, request: Request) -> list[HealingEventLogEntry]:
    manager = get_project_manager(request)
    project_dir = manager.project_dir(project_id)
    entries: list[HealingEventLogEntry] = []
    for env_dir in sorted((project_dir / "environments").glob("*")):
        entries.extend(HealingLogStore(env_dir).list(test_case_id))
    return entries


def _find_heal_id(root_dir: Path, heal_id: str) -> tuple[Path, str] | None:
    """Globally-unique `heal_id`, so no project/env context is needed up front —
    scan every environment's healing logs and return (env_dir, test_case_id) once found."""
    for path in root_dir.glob("projects/*/environments/*/healing_logs/*_healing.json"):
        env_dir = path.parent.parent
        test_case_id = path.name.removesuffix("_healing.json")
        for entry in HealingLogStore(env_dir).list(test_case_id):
            if entry.heal_id == heal_id:
                return env_dir, test_case_id
    return None


@router.post("/healing/{heal_id}/resolve")
def resolve_healing(heal_id: str, body: ResolveHealingRequest, request: Request) -> HealingEventLogEntry:
    manager = get_project_manager(request)
    found = _find_heal_id(manager.root_dir, heal_id)
    if found is None:
        raise HealingNotFoundError(f"heal {heal_id!r} not found")
    env_dir, test_case_id = found

    healing_log_store = HealingLogStore(env_dir)
    entries = healing_log_store.list(test_case_id)
    resolved_entry: HealingEventLogEntry | None = None
    for i, entry in enumerate(entries):
        if entry.heal_id != heal_id:
            continue
        resolution: Literal["accepted", "rejected"] = "accepted" if body.action == "accept" else "rejected"
        entries[i] = entry.model_copy(update={"resolution": resolution})
        resolved_entry = entries[i]
        break
    healing_log_store.replace(test_case_id, entries)

    # project_id is the first path segment after "projects/" in env_dir's ancestry.
    project_dir = env_dir.parent.parent
    test_case_store = TestCaseStore(project_dir)
    if body.action == "accept" and resolved_entry is not None and resolved_entry.candidates:
        best = resolved_entry.candidates[0]
        test_case = test_case_store.get(test_case_id)
        steps = list(test_case.steps)  # type: ignore[union-attr]
        step_index = int(resolved_entry.step_id)
        steps[step_index] = steps[step_index].model_copy(
            update={"target": LocatorTarget(strategy=best.strategy, value=best.value)}
        )
        test_case_store.update(test_case_id, steps=steps, status="approved", locator_confidence=best.confidence)
    else:
        test_case_store.update(test_case_id, status="approved")

    assert resolved_entry is not None
    return resolved_entry


@router.get("/runs/{run_id}/screenshots/{filename}")
def get_screenshot(run_id: str, filename: str, request: Request) -> FileResponse:
    if Path(filename).name != filename:
        raise HealingNotFoundError(f"invalid screenshot filename {filename!r}")
    manager = get_project_manager(request)
    for path in manager.root_dir.glob(f"projects/*/environments/*/runs/{run_id}/screenshots/{filename}"):
        return FileResponse(path)
    raise HealingNotFoundError(f"screenshot {filename!r} not found for run {run_id!r}")
