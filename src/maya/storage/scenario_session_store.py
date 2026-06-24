"""File-based CRUD for scenario submissions (F10), per plan.md §3.3
(`scenario_sessions/scenario_<timestamp>.json`). Much simpler than
`TestCaseStore` — one directory, no status-based subdirectories; status is
just a field updated in place."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from maya.storage.atomic import atomic_write_json
from maya.storage.models import ScenarioSession


class ScenarioSessionNotFoundError(LookupError):
    pass


class ScenarioSessionStore:
    def __init__(self, project_dir: Path) -> None:
        self._dir = Path(project_dir) / "scenario_sessions"

    def _path(self, session_id: str) -> Path:
        return self._dir / f"{session_id}.json"

    def ref_path(self, session_id: str) -> str:
        """Relative path (from the project dir) suitable for a test case's
        `source_scenario_ref`."""
        return f"scenario_sessions/{session_id}.json"

    def create(self, project_id: str, environment_id: str, text: str) -> ScenarioSession:
        # A short uuid suffix alongside the timestamp avoids filename collisions
        # between two submissions in the same millisecond (plausible in tests).
        session_id = f"scenario_{int(time.time() * 1000)}_{uuid4().hex[:6]}"
        session = ScenarioSession(
            id=session_id,
            project_id=project_id,
            environment_id=environment_id,
            text=text,
            submitted_at=datetime.now(UTC),
        )
        atomic_write_json(self._path(session_id), session)
        return session

    def get(self, session_id: str) -> ScenarioSession:
        path = self._path(session_id)
        if not path.exists():
            raise ScenarioSessionNotFoundError(f"scenario session {session_id!r} not found")
        return ScenarioSession.model_validate_json(path.read_bytes())

    def update(self, session_id: str, **fields: object) -> ScenarioSession:
        session = self.get(session_id)
        updated = session.model_copy(update=fields)
        atomic_write_json(self._path(session_id), updated)
        return updated
