"""`HealingEngine`: F9's classify -> fallback-hierarchy -> confidence-score -> apply/flag
pipeline, invoked inline by `ExecutionEngine` on locator/element-state failures
(plan.md §2.3 Self-Healing Engine row, §5.e). Tiers 1-5 are pure DOM/AX-tree signal
matching; tier 6 (vision LLM) is the only AI-queue-touching step, reached only as a
last resort once tiers 1-5 produce nothing and the failure has recurred enough times
to justify the AI-queue cost (`HealingConfig.vision_fallback_after_attempts`)."""

from __future__ import annotations

import difflib
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import uuid4

from playwright.sync_api import Error as PlaywrightError

from maya.adapters.browser_driver import BrowserDriver
from maya.adapters.llm_client import LLMClient
from maya.perception.elements import extract_elements
from maya.perception.snapshot_engine import ViewSnapshotEngine
from maya.storage.atomic import atomic_write_bytes
from maya.storage.healing_log_store import HealingLogStore
from maya.storage.models import (
    HealingCandidate,
    HealingEventLogEntry,
    LocatorTarget,
    UIStep,
    UITestCase,
    ViewSnapshotElement,
    ViewSnapshotRecord,
)
from maya.storage.test_case_store import TestCaseStore

logger = logging.getLogger("maya.healing")

FailureType = Literal["locator_not_found", "element_changed_state", "assertion_failure", "timeout"]

_HEALABLE: frozenset[str] = frozenset({"locator_not_found", "element_changed_state"})

_TASK_ROLE = "ui_explore_heal"

_MIN_FLOOR = 0.3

_WEIGHTS = {"attribute": 0.35, "stability": 0.20, "specificity": 0.20, "context": 0.15, "visual": 0.10}

_VISION_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


# --- F9-010: failure classification -----------------------------------------------


def classify_failure(exc: Exception) -> FailureType:
    """`playwright.sync_api.TimeoutError` is a subclass of `Error` and is what
    Playwright actually raises for *both* "locator never matched anything" and
    "locator matched but the element never became actionable" — its auto-wait
    actionability checks wrap every click/fill/etc, so a bare `isinstance` check
    can't distinguish them (confirmed empirically: both cases raise `TimeoutError`,
    only the message differs). Playwright's call-log only logs `"locator resolved to
    ..."` once the locator actually matched an element — its absence means the
    locator matched nothing at all."""
    if isinstance(exc, AssertionError):
        return "assertion_failure"
    if isinstance(exc, PlaywrightError):
        message = str(exc).lower()
        if "resolved to" in message:
            return "element_changed_state"
        return "locator_not_found"
    # Unrecognized exception type — default to locator_not_found so healing still
    # gets a chance rather than silently hard-failing on an unfamiliar error shape.
    return "locator_not_found"


# --- locator derivation -------------------------------------------------------------


def _locator_for(el: ViewSnapshotElement) -> LocatorTarget:
    """Prefer the most specific Playwright-resolvable strategy available on a
    candidate element: a stable test-id beats visible text beats bare role."""
    if el.data_testid:
        return LocatorTarget(strategy="test_id", value=el.data_testid)
    if el.name:
        return LocatorTarget(strategy="text", value=el.name)
    return LocatorTarget(strategy="role", value=el.role or "")


def _ref_parent(ref: str) -> list[str]:
    return ref.split(":")[-1].split(".")[:-1]


# --- F9-020/030/040/050: tiered candidate generation --------------------------------


def tier1_testid_exact(
    original_el: ViewSnapshotElement | None, current_elements: list[ViewSnapshotElement]
) -> list[tuple[HealingCandidate, ViewSnapshotElement]]:
    """Catches a non-testid locator breaking (text/role changed) while the element's
    own `data-testid` attribute stayed stable — pivot to that stable anchor."""
    if original_el is None or not original_el.data_testid:
        return []
    out = []
    for el in current_elements:
        if el.data_testid == original_el.data_testid:
            candidate = HealingCandidate(
                strategy="test_id", value=el.data_testid, confidence=0.0,
                signal_breakdown={"attribute": 1.0},
            )
            out.append((candidate, el))
    return out


def tier2_aria_role(
    original_el: ViewSnapshotElement | None, current_elements: list[ViewSnapshotElement]
) -> list[tuple[HealingCandidate, ViewSnapshotElement]]:
    """Catches the textbook rename case: the element's accessible role+name is
    unchanged even though its data-testid attribute value changed."""
    if original_el is None or original_el.role is None:
        return []
    out = []
    for el in current_elements:
        if el.role != original_el.role:
            continue
        if original_el.name and el.name == original_el.name:
            raw = 1.0
        elif original_el.name is None and el.name is None:
            raw = 0.6
        else:
            continue
        candidate = HealingCandidate(
            strategy=_locator_for(el).strategy, value=_locator_for(el).value, confidence=0.0,
            signal_breakdown={"attribute": raw},
        )
        out.append((candidate, el))
    return out


def tier3_fuzzy_text(
    original_el: ViewSnapshotElement | None, current_elements: list[ViewSnapshotElement]
) -> list[tuple[HealingCandidate, ViewSnapshotElement]]:
    if original_el is None or not original_el.name:
        return []
    out = []
    for el in current_elements:
        if not el.name:
            continue
        ratio = difflib.SequenceMatcher(None, original_el.name, el.name).ratio()
        if ratio < _MIN_FLOOR:
            continue
        locator = _locator_for(el)
        candidate = HealingCandidate(
            strategy=locator.strategy, value=locator.value, confidence=0.0,
            signal_breakdown={"attribute": ratio},
        )
        out.append((candidate, el))
    return out


def tier4_relative_position(
    original_el: ViewSnapshotElement | None, current_elements: list[ViewSnapshotElement]
) -> list[tuple[HealingCandidate, ViewSnapshotElement]]:
    """Exact `path_fingerprint` match: the element didn't move in the tree and its
    role is unchanged, even if every other attribute (testid, name) is now different."""
    if original_el is None or not original_el.path_fingerprint:
        return []
    out = []
    for el in current_elements:
        if el.path_fingerprint == original_el.path_fingerprint:
            locator = _locator_for(el)
            candidate = HealingCandidate(
                strategy=locator.strategy, value=locator.value, confidence=0.0,
                signal_breakdown={"attribute": 1.0},
            )
            out.append((candidate, el))
    return out


def tier5_xpath_similarity(
    original_el: ViewSnapshotElement | None, current_elements: list[ViewSnapshotElement]
) -> list[tuple[HealingCandidate, ViewSnapshotElement]]:
    """Edit-distance-style similarity over the AX-tree path `ref`, comparing path
    *segments* as tokens (not raw characters — short numeric segments like "0.1.2"
    look spuriously similar under character-level diffing) — catches an element that
    moved to a structurally similar position."""
    if original_el is None or not original_el.ref:
        return []
    original_segments = original_el.ref.split(":")[-1].split(".")
    out = []
    for el in current_elements:
        if not el.ref:
            continue
        candidate_segments = el.ref.split(":")[-1].split(".")
        ratio = difflib.SequenceMatcher(None, original_segments, candidate_segments).ratio()
        if ratio < _MIN_FLOOR:
            continue
        locator = _locator_for(el)
        candidate = HealingCandidate(
            strategy=locator.strategy, value=locator.value, confidence=0.0,
            signal_breakdown={"attribute": ratio},
        )
        out.append((candidate, el))
    return out


_TIERS = (tier1_testid_exact, tier2_aria_role, tier3_fuzzy_text, tier4_relative_position, tier5_xpath_similarity)


def _vision_prompt(ax_tree: str, original_el: ViewSnapshotElement | None, original_locator: LocatorTarget) -> str:
    description = (
        f"role={original_el.role!r} name={original_el.name!r}" if original_el is not None
        else f"strategy={original_locator.strategy!r} value={original_locator.value!r}"
    )
    return (
        "A UI test's locator no longer resolves on this page. The element it used to "
        f"target was approximately: {description}. Using the AX-tree below and the "
        "attached screenshot, identify the single most likely replacement element. "
        "Respond with ONLY a JSON object: "
        '{"strategy": "test_id"|"role"|"text"|"label"|"css"|"xpath", "value": "...", '
        '"confidence": <0.0-1.0>}\n\n'
        f"AX-tree:\n{ax_tree}"
    )


def tier6_vision_llm(
    llm: LLMClient,
    ax_tree: str,
    screenshot: bytes,
    original_el: ViewSnapshotElement | None,
    original_locator: LocatorTarget,
) -> list[HealingCandidate]:
    """Last resort: combined DOM+vision re-grounding via one multimodal LLM call.
    Never pass `tools=` for `task_role="ui_explore_heal"` — qwen2.5vl (the only model
    configured for it) rejects any request containing `tools` with an HTTP 400 rather
    than degrading gracefully (confirmed against a live Ollama instance), so the
    fallback JSON-object-in-text format is used unconditionally, not as a fallback."""
    prompt = _vision_prompt(ax_tree, original_el, original_locator)
    response = llm.generate(prompt, images=[screenshot], task_role=_TASK_ROLE)
    match = _VISION_JSON_RE.search(response.text or "")
    if not match:
        logger.warning("healing vision tier: could not parse a JSON object from LLM response")
        return []
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        logger.warning("healing vision tier: LLM response was not valid JSON")
        return []
    strategy, value = payload.get("strategy"), payload.get("value")
    if not strategy or not value:
        return []
    raw_confidence = max(0.0, min(1.0, float(payload.get("confidence", 0.5))))
    return [
        HealingCandidate(
            strategy=strategy, value=value, confidence=0.0,
            signal_breakdown={"attribute": raw_confidence, "visual": raw_confidence},
        )
    ]


# --- F9-060: confidence scoring ------------------------------------------------------


def _stability(candidate_el: ViewSnapshotElement | None, recent_snapshots: list[ViewSnapshotRecord]) -> float:
    if candidate_el is None:
        return 0.5
    if not recent_snapshots:
        # No prior snapshot history at all — absence-as-trust, not distrust, so a
        # heal's very first occurrence on a fresh view isn't penalized for it.
        return 1.0
    # `path_fingerprint` first, not `data_testid`: a rename's whole point is that the
    # candidate's testid value is *new* (by definition never seen before), so keying
    # on it would make every first-time rename heal score 0 on this signal. The
    # structural position (path_fingerprint) is what plausibly persisted across a
    # pure attribute-value change, so it's the more meaningful stability anchor.
    key = candidate_el.path_fingerprint or candidate_el.data_testid
    if not key:
        return 0.5
    seen = sum(
        1
        for snap in recent_snapshots
        if any((e.path_fingerprint or e.data_testid) == key for e in snap.elements)
    )
    return seen / len(recent_snapshots)


def _context_match(original_el: ViewSnapshotElement | None, candidate_el: ViewSnapshotElement | None) -> float:
    if original_el is None or candidate_el is None or not original_el.ref or not candidate_el.ref:
        return 0.5
    # Equal parent paths count as a match even when both are empty (top-level
    # siblings, e.g. elements with no AX-tree landmark wrapper) — that's still
    # consistent context, not missing data.
    return 1.0 if _ref_parent(original_el.ref) == _ref_parent(candidate_el.ref) else 0.0


def score_candidate(
    candidate: HealingCandidate,
    original_el: ViewSnapshotElement | None,
    candidate_el: ViewSnapshotElement | None,
    tier_candidate_count: int,
    recent_snapshots: list[ViewSnapshotRecord],
) -> HealingCandidate:
    attribute = candidate.signal_breakdown.get("attribute", 0.0)
    stability = _stability(candidate_el, recent_snapshots)
    specificity = 1.0 / max(tier_candidate_count, 1)
    context = _context_match(original_el, candidate_el)
    visual = candidate.signal_breakdown.get("visual", 0.5)

    confidence = (
        _WEIGHTS["attribute"] * attribute
        + _WEIGHTS["stability"] * stability
        + _WEIGHTS["specificity"] * specificity
        + _WEIGHTS["context"] * context
        + _WEIGHTS["visual"] * visual
    )
    confidence = max(0.0, min(1.0, confidence))
    return candidate.model_copy(
        update={
            "confidence": confidence,
            "signal_breakdown": {
                "attribute": attribute, "stability": stability,
                "specificity": specificity, "context": context, "visual": visual,
            },
        }
    )


# --- F9-070/080/090: orchestration ---------------------------------------------------


@dataclass
class HealResult:
    applied: HealingCandidate | None
    auto_applied: bool
    candidates: list[HealingCandidate]
    escalated_to_vision: bool
    patched_step: UIStep | None
    log_entry: HealingEventLogEntry
    needs_review: bool = False


class HealingEngine:
    def __init__(
        self,
        llm: LLMClient,
        snapshot_engine: ViewSnapshotEngine,
        test_case_store: TestCaseStore,
        healing_log_store: HealingLogStore,
        project_id: str,
        env_id: str,
        run_id: str,
        screenshots_dir: Path | None = None,
        auto_apply_threshold: float = 0.90,
        vision_fallback_after_attempts: int = 2,
    ) -> None:
        self._llm = llm
        self._snapshot_engine = snapshot_engine
        self._test_case_store = test_case_store
        self._healing_log_store = healing_log_store
        self._project_id = project_id
        self._env_id = env_id
        self._run_id = run_id
        self._screenshots_dir = screenshots_dir
        self._auto_apply_threshold = auto_apply_threshold
        self._vision_fallback_after_attempts = vision_fallback_after_attempts

    def _find_original_element(
        self, tc: UITestCase, target: LocatorTarget | None
    ) -> ViewSnapshotElement | None:
        if target is None:
            return None
        snapshot = self._snapshot_engine.load_latest(self._project_id, self._env_id, tc.view_identity)
        if snapshot is None:
            return None
        if target.strategy == "test_id":
            for el in snapshot.elements:
                if el.data_testid == target.value:
                    return el
            return None
        for el in snapshot.elements:
            if el.name == target.value or el.role == target.value:
                return el
        return None

    def _unresolved_attempts(self, test_case_id: str, step_id: str) -> int:
        count = 0
        for entry in reversed(self._healing_log_store.list(test_case_id)):
            if entry.step_id != step_id:
                continue
            if entry.applied is not None:
                break
            count += 1
        return count

    def heal(
        self,
        driver: BrowserDriver,
        tc: UITestCase,
        step_index: int,
        failure_type: FailureType,
        exc: Exception,
    ) -> HealResult:
        step = tc.steps[step_index]
        step_id = str(step_index)
        original_locator = step.target
        heal_id = uuid4().hex

        if failure_type not in _HEALABLE:
            entry = HealingEventLogEntry(
                heal_id=heal_id, run_id=self._run_id, step_id=step_id, failure_type=failure_type,
                original_locator=original_locator.model_dump() if original_locator else None,
            )
            return HealResult(None, False, [], False, None, entry)

        original_el = self._find_original_element(tc, original_locator)
        current_elements = extract_elements(driver.get_ax_tree(), driver.get_dom_html())
        recent_snapshots = self._snapshot_engine.load_recent(
            self._project_id, self._env_id, tc.view_identity, 3
        )

        scored: list[tuple[HealingCandidate, ViewSnapshotElement]] = []
        for tier in _TIERS:
            raw_pairs = tier(original_el, current_elements)
            if not raw_pairs:
                continue
            for candidate, el in raw_pairs:
                scored.append((score_candidate(candidate, original_el, el, len(raw_pairs), recent_snapshots), el))
            if any(c.confidence >= _MIN_FLOOR for c, _ in scored):
                break

        escalated_to_vision = False
        if not scored:
            prior_unresolved = self._unresolved_attempts(tc.id, step_id)
            if prior_unresolved + 1 >= self._vision_fallback_after_attempts:
                escalated_to_vision = True
                vision_screenshot = driver.screenshot()
                if self._screenshots_dir is not None:
                    self._screenshots_dir.mkdir(parents=True, exist_ok=True)
                    atomic_write_bytes(self._screenshots_dir / f"heal_{heal_id}.png", vision_screenshot)
                vision_candidates = tier6_vision_llm(
                    self._llm, driver.get_ax_tree(), vision_screenshot, original_el,
                    original_locator or LocatorTarget(strategy="unknown", value=""),
                )
                for candidate in vision_candidates:
                    scored.append((score_candidate(candidate, original_el, None, len(vision_candidates), recent_snapshots), None))

        candidates = sorted((c for c, _ in scored), key=lambda c: c.confidence, reverse=True)
        best = candidates[0] if candidates else None

        applied: HealingCandidate | None = None
        auto_applied = False
        patched_step: UIStep | None = None
        needs_review = False

        if best is not None and best.confidence >= self._auto_apply_threshold:
            patched_step = step.model_copy(update={"target": LocatorTarget(strategy=best.strategy, value=best.value)})
            patched_steps = list(tc.steps)
            patched_steps[step_index] = patched_step
            self._test_case_store.update(tc.id, steps=patched_steps, locator_confidence=best.confidence)
            applied, auto_applied = best, True
        elif best is not None:
            self._test_case_store.update(tc.id, status="needs_review")
            needs_review = True

        entry = HealingEventLogEntry(
            heal_id=heal_id, run_id=self._run_id, step_id=step_id, failure_type=failure_type,
            original_locator=original_locator.model_dump() if original_locator else None,
            candidates=candidates, applied=applied, auto_applied=auto_applied,
            escalated_to_vision=escalated_to_vision, escalated_to_llm=escalated_to_vision,
        )
        self._healing_log_store.append(tc.id, entry)

        return HealResult(applied, auto_applied, candidates, escalated_to_vision, patched_step, entry, needs_review)
