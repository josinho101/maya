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

    def get(self, test_case_id: str) -> UITestCase | APITestCase:
        for status in _STATUSES:
            path = self._tc_dir / status / f"{test_case_id}.json"
            if path.exists():
                return TestCaseAdapter.validate_json(path.read_bytes())
        raise FileNotFoundError(f"test case {test_case_id!r} not found in any status directory")

    def list(self, status: str) -> list[UITestCase | APITestCase]:
        if status not in _STATUSES:
            raise ValueError(f"unknown status {status!r}, expected one of {_STATUSES}")
        return [
            TestCaseAdapter.validate_json(path.read_bytes())
            for path in sorted((self._tc_dir / status).glob("tc_*.json"))
        ]

    def move(self, test_case_id: str, from_status: str, to_status: str) -> None:
        if from_status not in _STATUSES or to_status not in _STATUSES:
            raise ValueError(f"unknown status, expected one of {_STATUSES}")
        if from_status == to_status:
            raise ValueError("from_status and to_status must differ")

        src = self._tc_dir / from_status / f"{test_case_id}.json"
        if not src.exists():
            raise FileNotFoundError(f"test case {test_case_id!r} not found in {from_status!r}")

        test_case = TestCaseAdapter.validate_json(src.read_bytes())
        updated = test_case.model_copy(update={"status": to_status})
        dst = self._tc_dir / to_status / f"{test_case_id}.json"

        try:
            atomic_write_json(dst, updated)
        except FileExistsError:
            atomic_write_json(dst, updated)

        os.remove(src)
