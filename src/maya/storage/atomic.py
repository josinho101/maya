"""Atomic write-then-rename helper shared by TestCaseStore and the scaffolder
(and reused by ProjectManager in F3) to avoid corrupting JSON files on concurrent writes."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel


def atomic_write_bytes(path: Path, data: bytes) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_bytes(data)
    os.replace(tmp_path, path)


def atomic_write_json(path: Path, model: BaseModel) -> None:
    atomic_write_bytes(path, model.model_dump_json(indent=2).encode("utf-8"))
