"""`BrowserDriver` interface (plan.md §2.1, §2.3): Execution Engine (F7) and Self-Healing (F9)
depend on this Protocol only, never on Playwright directly.

`Locator` is `storage.models.LocatorTarget` re-exported under this name — the test-case schema
and the browser adapter already agree on the same `{strategy, value}` shape, so there is no
separate dataclass to keep in sync.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from maya.storage.models import LocatorTarget as Locator

__all__ = ["Locator", "BrowserDriver"]


@runtime_checkable
class BrowserDriver(Protocol):
    def navigate(self, url: str) -> None: ...

    def current_url(self) -> str: ...

    def click(self, locator: Locator) -> None: ...

    def type(self, locator: Locator, text: str) -> None: ...

    def get_ax_tree(self) -> str: ...

    def screenshot(self) -> bytes: ...

    def get_dom_html(self) -> str: ...

    def upload_file(self, locator: Locator, file_path: Path) -> None: ...

    def save_storage_state(self, path: Path) -> None: ...

    def load_storage_state(self, path: Path) -> None: ...
