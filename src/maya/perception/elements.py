"""`extract_elements`: F8-020 — walks the AX-tree into a flat `ViewSnapshotElement[]`
list, the granularity `ViewSnapshotEngine.diff()` (F8-010) compares element-by-element.
"""

from __future__ import annotations

import hashlib
import re

from maya.perception.ax_tree import node_name, node_role_and_children, parse_ax_tree
from maya.storage.models import ViewSnapshotElement

_TESTID_TAG_RE = re.compile(
    r'<[a-zA-Z][a-zA-Z0-9]*\b[^>]*\bdata-testid="([^"]+)"[^>]*>([^<]*)', re.DOTALL
)


def _testid_by_name(dom_html: str) -> dict[str, str]:
    """Best-effort index from an element's visible inner text to its `data-testid`,
    built by regex rather than a full HTML parser (no new dependency, matching the
    `_TITLE_RE`-style regex already used in `view_identity.py`). Looked up by the
    AX-tree node's accessible `name` when walking the tree below."""
    index: dict[str, str] = {}
    for testid, inner_text in _TESTID_TAG_RE.findall(dom_html):
        name = inner_text.strip()
        if name:
            index[name] = testid
    return index


def _path_fingerprint(path: tuple[int, ...], role: str | None) -> str:
    path_str = ".".join(str(p) for p in path)
    serialized = f"{path_str}:{role or ''}"
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:12]


def _walk(
    nodes: list[object],
    path: tuple[int, ...],
    testid_by_name: dict[str, str],
    out: list[ViewSnapshotElement],
) -> None:
    for index, node in enumerate(nodes):
        role, children = node_role_and_children(node)
        if role is None:
            continue
        node_path = path + (index,)
        name = node_name(node) or None
        out.append(
            ViewSnapshotElement(
                ref=f"el:{'.'.join(str(p) for p in node_path)}",
                role=role,
                name=name,
                data_testid=testid_by_name.get(name) if name else None,
                path_fingerprint=_path_fingerprint(node_path, role),
            )
        )
        _walk(children, node_path, testid_by_name, out)


def extract_elements(ax_tree: str, dom_html: str) -> list[ViewSnapshotElement]:
    testid_by_name = _testid_by_name(dom_html)
    out: list[ViewSnapshotElement] = []
    _walk(parse_ax_tree(ax_tree), (), testid_by_name, out)
    return out
