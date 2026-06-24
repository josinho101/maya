"""Structural fingerprint + heading signal: two of the three view-identity signals
combined by `ViewSnapshotEngine` into the composite key from plan.md §4.

`ax_tree` here is the YAML string returned by `BrowserDriver.get_ax_tree()`
(Playwright's `aria_snapshot()`), not a dict — parsed internally via PyYAML.
"""

from __future__ import annotations

import hashlib
import json
import re

from maya.perception.ax_tree import node_name as _node_name
from maya.perception.ax_tree import node_role_and_children as _node_role_and_children
from maya.perception.ax_tree import parse_ax_tree as _parse_ax_tree

_LANDMARK_ROLES = {
    "main",
    "navigation",
    "banner",
    "contentinfo",
    "region",
    "dialog",
    "alertdialog",
    "tabpanel",
    "form",
    "complementary",
    "search",
}

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def _landmark_skeleton(nodes: list[object]) -> list[dict]:
    """Collapse a list of AX-tree nodes to only landmark-role nodes, flattening
    through non-landmark wrappers while preserving nesting among landmarks."""
    skeleton: list[dict] = []
    for node in nodes:
        role, children = _node_role_and_children(node)
        descendant_landmarks = _landmark_skeleton(children)
        if role in _LANDMARK_ROLES:
            skeleton.append({"role": role, "children": descendant_landmarks})
        else:
            skeleton.extend(descendant_landmarks)
    return skeleton


def _find_heading(nodes: list[object]) -> str | None:
    for node in nodes:
        role, children = _node_role_and_children(node)
        if role == "heading":
            return _node_name(node)
        found = _find_heading(children)
        if found is not None:
            return found
    return None


def structural_fingerprint(ax_tree: str) -> str:
    """Hash of the main-content-container role/landmark structure, ignoring leaf
    text/accessible names — two trees differing only in text hash identically."""
    skeleton = _landmark_skeleton(_parse_ax_tree(ax_tree))
    serialized = json.dumps(skeleton, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def heading_signal(ax_tree: str, dom_html: str) -> str:
    """Active heading-role node text, falling back to `<title>` from the DOM."""
    heading = _find_heading(_parse_ax_tree(ax_tree))
    if heading:
        return heading
    match = _TITLE_RE.search(dom_html)
    return match.group(1).strip() if match else ""
