"""Derives URL/filesystem-safe ids from human-entered names — project/environment ids
are no longer user-typed, they're generated from the name/tag the user does enter."""

from __future__ import annotations

import re

_NON_SLUG_CHARS = re.compile(r"[^a-z0-9]+")
_MAX_SLUG_LEN = 64  # keep in sync with ProjectManager._SLUG_RE's {0,62} body + 2 boundary chars


class EmptySlugError(ValueError):
    pass


def slugify(name: str) -> str:
    value = name.strip().lower()
    value = _NON_SLUG_CHARS.sub("-", value)
    value = value.strip("-")
    if not value:
        raise EmptySlugError(f"{name!r} contains no usable characters for an id")
    if len(value) > _MAX_SLUG_LEN:
        value = value[:_MAX_SLUG_LEN].rstrip("-")
    return value
