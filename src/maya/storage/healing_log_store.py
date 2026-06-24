"""Append-only `HealingEventLogEntry[]` persistence, one file per (environment, test
case): `<env_dir>/healing_logs/<test_case_id>_healing.json` (plan.md §5.e step 4)."""

from __future__ import annotations

from pathlib import Path

from pydantic import TypeAdapter

from maya.storage.atomic import atomic_write_list_json
from maya.storage.models import HealingEventLogEntry

_HealingLogAdapter: TypeAdapter[list[HealingEventLogEntry]] = TypeAdapter(list[HealingEventLogEntry])


class HealingLogStore:
    def __init__(self, env_dir: Path) -> None:
        self._dir = Path(env_dir) / "healing_logs"

    def _path(self, test_case_id: str) -> Path:
        return self._dir / f"{test_case_id}_healing.json"

    def list(self, test_case_id: str) -> list[HealingEventLogEntry]:
        path = self._path(test_case_id)
        if not path.exists():
            return []
        return _HealingLogAdapter.validate_json(path.read_bytes())

    def append(self, test_case_id: str, entry: HealingEventLogEntry) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        entries = self.list(test_case_id)
        entries.append(entry)
        atomic_write_list_json(self._path(test_case_id), _HealingLogAdapter, entries)

    def find_by_heal_id(self, heal_id: str) -> tuple[HealingEventLogEntry, str] | None:
        """Linear scan over this environment's healing logs for a matching `heal_id`,
        returning the entry plus the owning test case id (recovered from the filename,
        since `HealingEventLogEntry` itself has no `test_case_id` field)."""
        for path in sorted(self._dir.glob("*_healing.json")):
            for entry in _HealingLogAdapter.validate_json(path.read_bytes()):
                if entry.heal_id == heal_id:
                    return entry, path.name.removesuffix("_healing.json")
        return None

    def replace(self, test_case_id: str, entries: list[HealingEventLogEntry]) -> None:
        """Rewrite the full log for a test case — used to layer a `resolution` onto
        an existing entry without disturbing the rest of the append-only history."""
        self._dir.mkdir(parents=True, exist_ok=True)
        atomic_write_list_json(self._path(test_case_id), _HealingLogAdapter, entries)
