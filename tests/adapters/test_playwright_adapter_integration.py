from __future__ import annotations

from pathlib import Path

import pytest

from maya.adapters.browser_driver import Locator
from maya.adapters.playwright_adapter import PlaywrightAdapter

SAMPLE_FILE = Path(__file__).parent.parent / "fixtures" / "sample.png"


def _make_driver() -> PlaywrightAdapter:
    try:
        return PlaywrightAdapter(headless=True)
    except Exception as exc:  # noqa: BLE001 - environment-dependent (browser not installed)
        pytest.skip(f"Playwright browser not available: {exc}")


@pytest.mark.integration
def test_playwright_adapter_full_chain(demo_app_url):
    driver = _make_driver()
    try:
        driver.navigate(demo_app_url)

        username_locator = Locator(strategy="css", value="#username")
        driver.type(username_locator, "alice")
        assert driver._page.input_value("#username") == "alice"

        driver.click(Locator(strategy="test_id", value="counter-button"))
        assert "Count: 1" in driver.get_dom_html()

        png = driver.screenshot()
        assert isinstance(png, bytes) and len(png) > 0

        ax_tree = driver.get_ax_tree()
        assert isinstance(ax_tree, str)
        assert "textbox" in ax_tree

        driver.upload_file(Locator(strategy="test_id", value="upload-input"), SAMPLE_FILE)
    finally:
        driver.close()


@pytest.mark.integration
def test_playwright_adapter_storage_state_roundtrip(demo_app_url, tmp_path):
    state_path = tmp_path / "state.json"
    driver = _make_driver()
    try:
        driver.navigate(demo_app_url)
        driver._page.evaluate("() => localStorage.setItem('session', 'logged-in')")
        driver.save_storage_state(state_path)
        assert state_path.exists()

        driver.load_storage_state(state_path)
        driver.navigate(demo_app_url)
        value = driver._page.evaluate("() => localStorage.getItem('session')")
        assert value == "logged-in"
    finally:
        driver.close()
