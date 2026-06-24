"""File-based CRUD across the pending/approved/archived lifecycle directories.

The single chokepoint every agent/engine writes test cases through — no other
component should touch ``test_cases/{pending,approved,archived}/`` directly.
"""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from maya.storage.atomic import atomic_write_json
from maya.storage.models import APITestCase, TestCaseAdapter, UITestCase

_STATUSES = ("pending", "approved", "archived")


class TestCaseNotFoundError(FileNotFoundError):
    __test__ = False  # not a pytest test class despite the name


class TestCaseStatusConflictError(RuntimeError):
    __test__ = False  # not a pytest test class despite the name


class TestCaseStore:
    __test__ = False  # not a pytest test class despite the name

    def __init__(self, root_dir: Path) -> None:
        self._tc_dir = Path(root_dir) / "test_cases"

    def create(self, test_case: UITestCase | APITestCase) -> str:
        if not test_case.id:
            test_case = test_case.model_copy(update={"id": f"tc_{uuid4().hex}"})
        path = self._tc_dir / test_case.status / f"{test_case.id}.json"
        atomic_write_json(path, test_case)
        return test_case.id

    def find(self, test_case_id: str) -> tuple[UITestCase | APITestCase, str]:
        for status in _STATUSES:
            path = self._tc_dir / status / f"{test_case_id}.json"
            if path.exists():
                return TestCaseAdapter.validate_json(path.read_bytes()), status
        raise TestCaseNotFoundError(f"test case {test_case_id!r} not found in any status directory")

    def get(self, test_case_id: str) -> UITestCase | APITestCase:
        return self.find(test_case_id)[0]

    def list(self, status: str) -> list[UITestCase | APITestCase]:
        if status == "needs_review":
            return [tc for tc in self.list("approved") if tc.status == "needs_review"]
        if status not in _STATUSES:
            raise ValueError(f"unknown status {status!r}, expected one of {_STATUSES}")
        return [
            TestCaseAdapter.validate_json(path.read_bytes())
            for path in sorted((self._tc_dir / status).glob("tc_*.json"))
        ]

    def update(self, test_case_id: str, **fields: object) -> UITestCase | APITestCase:
        test_case, status = self.find(test_case_id)
        # A directory-status value is only allowed here when it matches the
        # directory the file already lives in (e.g. clearing a "needs_review" field
        # flag back to "approved" while the file never left approved/) — an actual
        # cross-directory move must go through move() instead.
        if fields.get("status") in _STATUSES and fields["status"] != status:
            raise ValueError("update() cannot move between pending/approved/archived — use move() instead")
        updated = test_case.model_copy(update=fields)
        atomic_write_json(self._tc_dir / status / f"{test_case_id}.json", updated)
        return updated

    def move(
        self, test_case_id: str, from_status: str, to_status: str, **extra_fields: object
    ) -> UITestCase | APITestCase:
        if from_status not in _STATUSES or to_status not in _STATUSES:
            raise ValueError(f"unknown status, expected one of {_STATUSES}")
        if from_status == to_status:
            raise ValueError("from_status and to_status must differ")

        test_case, current_status = self.find(test_case_id)
        if current_status != from_status:
            raise TestCaseStatusConflictError(
                f"test case {test_case_id!r} is in {current_status!r}, not {from_status!r}"
            )

        updated = test_case.model_copy(update={**extra_fields, "status": to_status})
        src = self._tc_dir / from_status / f"{test_case_id}.json"
        dst = self._tc_dir / to_status / f"{test_case_id}.json"
        atomic_write_json(dst, updated)
        os.remove(src)
        return updated
