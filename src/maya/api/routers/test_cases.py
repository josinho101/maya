"""REST CRUD for the pending/approved/archived test case review workflow (F6),
per plan.md §5.c. Routes are nested under /projects/{project_id}/test-cases — unlike
the spec doc's flattened shorthand — because TestCaseStore is constructed per-project
and there is no global index to resolve a bare test_case_id against."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from maya.managers.project_manager import ProjectManager
from maya.storage.models import APITestCase, UIStep, UITestCase
from maya.storage.test_case_store import TestCaseStore

router = APIRouter(prefix="/api/v1/projects", tags=["test-cases"])


def get_project_manager(request: Request) -> ProjectManager:
    return request.app.state.project_manager


def get_test_case_store(project_id: str, request: Request) -> TestCaseStore:
    manager = get_project_manager(request)
    return TestCaseStore(manager.project_dir(project_id))


class RejectRequest(BaseModel):
    reason: str


class PatchTestCaseRequest(BaseModel):
    steps: list[UIStep] | None = None


@router.get("/{project_id}/test-cases")
def list_test_cases(
    project_id: str,
    request: Request,
    status: Literal["pending", "approved", "needs_review", "archived"] = "pending",
    protocol: Literal["ui", "api"] | None = None,
) -> list[UITestCase | APITestCase]:
    store = get_test_case_store(project_id, request)
    cases = store.list(status)
    if protocol is not None:
        cases = [c for c in cases if c.protocol == protocol]
    return cases


@router.post("/{project_id}/test-cases/{test_case_id}/approve")
def approve_test_case(
    project_id: str, test_case_id: str, request: Request
) -> UITestCase | APITestCase:
    store = get_test_case_store(project_id, request)
    return store.move(test_case_id, "pending", "approved")


@router.post("/{project_id}/test-cases/{test_case_id}/reject")
def reject_test_case(
    project_id: str, test_case_id: str, body: RejectRequest, request: Request
) -> UITestCase | APITestCase:
    store = get_test_case_store(project_id, request)
    return store.move(test_case_id, "pending", "archived", rejection_reason=body.reason)


@router.patch("/{project_id}/test-cases/{test_case_id}")
def patch_test_case(
    project_id: str, test_case_id: str, body: PatchTestCaseRequest, request: Request
) -> UITestCase | APITestCase:
    store = get_test_case_store(project_id, request)
    test_case, _ = store.find(test_case_id)
    if not isinstance(test_case, UITestCase):
        raise HTTPException(422, f"test case {test_case_id!r} has no steps to edit")
    fields = {name: value for name, value in body if name in body.model_fields_set}
    return store.update(test_case_id, **fields)
