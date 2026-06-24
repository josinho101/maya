"""`ExecutionEngine.run_test_case`: deterministic interpreter for approved UI test
cases (plan.md §2.3, F7-010). Resolves each step's locator via the `BrowserDriver`
methods (which already call `resolve_locator` per F2-070), evaluates the step's
assertion (if any) against the post-action DOM, and captures a screenshot on
failure. No healing here — F9 wraps this failure path later without changing
this method's shape."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from maya.adapters.browser_driver import BrowserDriver
from maya.engines.assertions import evaluate_assertion
from maya.storage.atomic import atomic_write_bytes
from maya.storage.models import UIStep, UITestCase

_ACTIONS = ("click", "type", "upload_file")


@dataclass
class TestCaseResult:
    test_case_id: str
    status: str  # "pass" | "fail"
    execution_time_ms: int
    screenshot_refs: list[str] = field(default_factory=list)
    failure_reason: str | None = None


class ExecutionEngine:
    def __init__(self, driver: BrowserDriver, screenshots_dir: Path) -> None:
        self._driver = driver
        self._screenshots_dir = Path(screenshots_dir)

    def run_test_case(self, tc: UITestCase) -> TestCaseResult:
        total_ms = 0
        for index, step in enumerate(tc.steps):
            start = time.perf_counter()
            try:
                self._perform_step(step)
            except Exception as exc:  # noqa: BLE001 - any step failure ends the run cleanly
                total_ms += int((time.perf_counter() - start) * 1000)
                screenshot_ref = self._capture_failure_screenshot(tc.id, index)
                return TestCaseResult(
                    test_case_id=tc.id,
                    status="fail",
                    execution_time_ms=total_ms,
                    screenshot_refs=[screenshot_ref],
                    failure_reason=str(exc),
                )
            total_ms += int((time.perf_counter() - start) * 1000)

        return TestCaseResult(test_case_id=tc.id, status="pass", execution_time_ms=total_ms)

    def _perform_step(self, step: UIStep) -> None:
        if step.action in _ACTIONS:
            if step.target is None:
                raise ValueError(f"step action {step.action!r} requires a target")
            if step.action == "click":
                self._driver.click(step.target)
            elif step.action == "type":
                self._driver.type(step.target, step.input)
            else:
                self._driver.upload_file(step.target, Path(step.input))

        if step.assertion is not None:
            self._evaluate_assertion(step.assertion)

    def _evaluate_assertion(self, assertion: dict[str, Any]) -> None:
        actual = self._driver.get_dom_html()
        if not evaluate_assertion(assertion["type"], actual, assertion.get("value")):
            raise AssertionError(
                f"assertion {assertion['type']!r} failed against current page content "
                f"(expected={assertion.get('value')!r})"
            )

    def _capture_failure_screenshot(self, test_case_id: str, step_index: int) -> str:
        self._screenshots_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{test_case_id}_{step_index}.png"
        atomic_write_bytes(self._screenshots_dir / filename, self._driver.screenshot())
        return filename
