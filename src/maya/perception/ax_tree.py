"""Shared parsing helpers for the YAML AX-tree string returned by
`BrowserDriver.get_ax_tree()` (Playwright's `aria_snapshot()`). Used by both
`view_identity.py` (structural fingerprint / heading signal) and `elements.py`
(F8-020 element extraction) so the tree-walking logic isn't duplicated.
"""

from __future__ import annotations

import re

import yaml

_NAME_RE = re.compile(r'"([^"]*)"')


def node_role_and_children(node: object) -> tuple[str | None, list[object]]:
    """A YAML-parsed ARIA-snapshot node is either a leaf string (no element children),
    or a single-key mapping from its node string to either a list of element children
    or a plain text value (a text-content leaf, e.g. `{"paragraph": "some text"}`)."""
    if isinstance(node, str):
        text, value = node, []
    elif isinstance(node, dict) and len(node) == 1:
        (text, value), = node.items()
    else:
        return None, []
    children = value if isinstance(value, list) else []
    role = text.split()[0] if text and text.split() else None
    return role, children


def node_name(node: object) -> str:
    text = node if isinstance(node, str) else next(iter(node)) if isinstance(node, dict) else ""
    match = _NAME_RE.search(text)
    return match.group(1) if match else ""


def parse_ax_tree(ax_tree: str) -> list[object]:
    parsed = yaml.safe_load(ax_tree)
    return parsed if isinstance(parsed, list) else []
