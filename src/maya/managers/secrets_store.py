"""Secure per-project credential/config store + the `${secure.*}` placeholder
resolver, per plan.md §7. Not Pydantic-modeled by design — plan.md §7 describes this
as a flexible key-value/document store, not a fixed schema."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from maya.storage.atomic import atomic_write_bytes


class SecretNotFoundError(LookupError):
    pass


class SecretsStore:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = Path(root_dir)
        self.secure_dir = self.root_dir / "config" / "secure"

    def _path(self, project_id: str) -> Path:
        return self.secure_dir / f"{project_id}.secure.json"

    def _read_all(self, project_id: str) -> dict[str, dict[str, str]]:
        path = self._path(project_id)
        if not path.exists():
            return {}
        return json.loads(path.read_text())

    def get(self, project_id: str, env_id: str, key: str) -> str:
        data = self._read_all(project_id)
        try:
            return data[env_id][key]
        except KeyError as exc:
            raise SecretNotFoundError(f"{project_id}.{env_id}.{key}") from exc

    def set(self, project_id: str, env_id: str, key: str, value: str) -> None:
        self.secure_dir.mkdir(parents=True, exist_ok=True)
        data = self._read_all(project_id)
        data.setdefault(env_id, {})[key] = value
        atomic_write_bytes(self._path(project_id), json.dumps(data, indent=2).encode("utf-8"))


_PLACEHOLDER_RE = re.compile(r"\$\{secure\.([^.}]+)\.([^.}]+)\.([^}]+)\}")


def resolve_placeholder(template: str, secrets: SecretsStore) -> str:
    """Substitutes every ${secure.<project>.<env>.<key>} occurrence in `template`
    via `secrets.get(...)`. `secrets` only needs to satisfy `.get(project, env, key)`,
    so tests can pass a stub instead of a real SecretsStore."""

    def _sub(match: re.Match[str]) -> str:
        project_id, env_id, key = match.group(1), match.group(2), match.group(3)
        return secrets.get(project_id, env_id, key)

    return _PLACEHOLDER_RE.sub(_sub, template)


def resolve_strings(value: Any, secrets: SecretsStore) -> Any:
    """Recursively resolves every string leaf in a nested dict/list structure,
    so a whole package dict can be resolved without per-field-name special-casing."""
    if isinstance(value, str):
        return resolve_placeholder(value, secrets)
    if isinstance(value, dict):
        return {k: resolve_strings(v, secrets) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve_strings(v, secrets) for v in value]
    return value
