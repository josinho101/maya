from __future__ import annotations

from pathlib import Path

from maya.adapters.browser_driver import BrowserDriver, Locator


class StubBrowserDriver:
    def navigate(self, url: str) -> None: ...

    def current_url(self) -> str:
        return ""

    def click(self, locator: Locator) -> None: ...

    def type(self, locator: Locator, text: str) -> None: ...

    def get_ax_tree(self) -> str:
        return ""

    def screenshot(self) -> bytes:
        return b""

    def get_dom_html(self) -> str:
        return ""

    def upload_file(self, locator: Locator, file_path: Path) -> None: ...

    def save_storage_state(self, path: Path) -> None: ...

    def load_storage_state(self, path: Path) -> None: ...


def test_stub_satisfies_browser_driver_protocol():
    assert isinstance(StubBrowserDriver(), BrowserDriver)


def test_non_conforming_object_does_not_satisfy_protocol():
    assert not isinstance(object(), BrowserDriver)


def test_locator_is_the_shared_storage_model():
    locator = Locator(strategy="test_id", value="login-button")
    assert locator.strategy == "test_id"
    assert locator.value == "login-button"
