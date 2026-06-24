"""Concrete `BrowserDriver` backed by Playwright's sync API (plan.md §2.3) — sync because the
agent perception->reasoning->action loop is inherently sequential, never concurrent within one job.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from maya.adapters.browser_driver import BrowserDriver, Locator

_STRATEGY_RESOLVERS: dict[str, Callable[[Page, str], Any]] = {
    "test_id": lambda page, value: page.get_by_test_id(value),
    "role": lambda page, value: page.get_by_role(value),
    "text": lambda page, value: page.get_by_text(value),
    "label": lambda page, value: page.get_by_label(value),
    "css": lambda page, value: page.locator(value),
    "xpath": lambda page, value: page.locator(f"xpath={value}"),
}


def resolve_locator(page: Page, locator: Locator) -> Any:
    """Strategy -> Playwright locator. Reused as-is by F9's self-healing fallback hierarchy."""
    try:
        resolver = _STRATEGY_RESOLVERS[locator.strategy]
    except KeyError:
        raise ValueError(f"unknown locator strategy: {locator.strategy!r}") from None
    return resolver(page, locator.value)


class PlaywrightAdapter(BrowserDriver):
    def __init__(self, headless: bool = True, storage_state: Path | None = None) -> None:
        self._playwright = sync_playwright().start()
        self._browser: Browser = self._playwright.chromium.launch(headless=headless)
        self._context: BrowserContext = self._browser.new_context(
            storage_state=str(storage_state) if storage_state else None
        )
        self._page: Page = self._context.new_page()

    def __enter__(self) -> PlaywrightAdapter:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        self._context.close()
        self._browser.close()
        self._playwright.stop()

    def navigate(self, url: str) -> None:
        self._page.goto(url)

    def current_url(self) -> str:
        return self._page.url

    def click(self, locator: Locator) -> None:
        resolve_locator(self._page, locator).click()

    def type(self, locator: Locator, text: str) -> None:
        resolve_locator(self._page, locator).fill(text)

    def get_ax_tree(self) -> str:
        return self._page.aria_snapshot()

    def screenshot(self) -> bytes:
        return self._page.screenshot()

    def get_dom_html(self) -> str:
        return self._page.content()

    def upload_file(self, locator: Locator, file_path: Path) -> None:
        resolve_locator(self._page, locator).set_input_files(str(file_path))

    def save_storage_state(self, path: Path) -> None:
        self._context.storage_state(path=str(path))

    def load_storage_state(self, path: Path) -> None:
        self._context.close()
        self._context = self._browser.new_context(storage_state=str(path))
        self._page = self._context.new_page()
