from __future__ import annotations

from playwright.sync_api import Error as PlaywrightError

from maya.adapters.llm_client import LLMResponse
from maya.engines.healing_engine import (
    classify_failure,
    score_candidate,
    tier1_testid_exact,
    tier2_aria_role,
    tier3_fuzzy_text,
    tier4_relative_position,
    tier5_xpath_similarity,
    tier6_vision_llm,
)
from maya.storage.models import LocatorTarget, ViewSnapshotElement


def _el(ref, role, name, data_testid=None, path_fingerprint=None) -> ViewSnapshotElement:
    return ViewSnapshotElement(ref=ref, role=role, name=name, data_testid=data_testid, path_fingerprint=path_fingerprint)


def test_classify_failure_assertion():
    assert classify_failure(AssertionError("assertion 'equals' failed")) == "assertion_failure"


def test_classify_failure_element_changed_state():
    # Empirically confirmed shape of a real Playwright TimeoutError when the locator
    # *did* resolve to an element but it never became actionable (e.g. hidden) —
    # `TimeoutError` is a subclass of `Error` and is raised in both this case and the
    # "never found" case below, so the classifier keys off "resolved to" in the
    # message, not the exception type.
    exc = PlaywrightError(
        'Locator.click: Timeout 2000ms exceeded.\nCall log:\n'
        '  - waiting for locator("#settings-panel")\n'
        '    - locator resolved to <section hidden>…</section>\n'
        '    - element is not visible\n'
    )
    assert classify_failure(exc) == "element_changed_state"


def test_classify_failure_locator_not_found():
    exc = PlaywrightError(
        'Locator.click: Timeout 2000ms exceeded.\nCall log:\n'
        '  - waiting for get_by_test_id("does-not-exist")\n'
    )
    assert classify_failure(exc) == "locator_not_found"


def test_classify_failure_unknown_exception_defaults_to_locator_not_found():
    assert classify_failure(RuntimeError("something else broke")) == "locator_not_found"


def test_tier1_testid_exact_match():
    original = _el("el:0", "button", "Count: 0", data_testid="counter-button")
    current = [
        _el("el:0", "button", "Renamed text entirely", data_testid="counter-button"),
        _el("el:1", "button", "Settings", data_testid="reveal-panel-button"),
    ]
    pairs = tier1_testid_exact(original, current)
    assert len(pairs) == 1
    candidate, el = pairs[0]
    assert candidate.strategy == "test_id"
    assert candidate.value == "counter-button"
    assert el.ref == "el:0"


def test_tier1_no_match_without_original_testid():
    original = _el("el:0", "button", "Count: 0")
    current = [_el("el:0", "button", "Count: 0", data_testid="counter-button")]
    assert tier1_testid_exact(original, current) == []


def test_tier2_aria_role_exact_rename():
    original = _el("el:0", "button", "Count: 0", data_testid="counter-button")
    current = [
        _el("el:0", "button", "Count: 0", data_testid="counter-button-v2"),
        _el("el:1", "button", "Settings", data_testid="reveal-panel-button"),
    ]
    pairs = tier2_aria_role(original, current)
    assert len(pairs) == 1
    candidate, el = pairs[0]
    assert el.data_testid == "counter-button-v2"
    assert candidate.signal_breakdown["attribute"] == 1.0


def test_tier3_fuzzy_text_match():
    original = _el("el:0", "button", "Count: 0")
    current = [
        _el("el:0", "button", "Count: 1"),
        _el("el:1", "button", "Settings"),
    ]
    pairs = tier3_fuzzy_text(original, current)
    assert pairs
    best_candidate, best_el = max(pairs, key=lambda p: p[0].signal_breakdown["attribute"])
    assert best_el.name == "Count: 1"


def test_tier4_relative_position_exact_fingerprint():
    original = _el("el:0", "button", "Count: 0", path_fingerprint="abc123")
    current = [
        _el("el:0", "button", "totally different", data_testid="new-id", path_fingerprint="abc123"),
        _el("el:1", "button", "Settings", path_fingerprint="def456"),
    ]
    pairs = tier4_relative_position(original, current)
    assert len(pairs) == 1
    assert pairs[0][1].path_fingerprint == "abc123"


def test_tier5_xpath_similarity_ranking():
    original = _el("el:0.1.2", "button", "Count: 0")
    current = [
        _el("el:0.1.3", "button", "x"),  # same grandparent+parent, leaf index differs
        _el("el:0.9.9", "button", "y"),  # only top-level segment shared
    ]
    pairs = tier5_xpath_similarity(original, current)
    ranked = sorted(pairs, key=lambda p: p[0].signal_breakdown["attribute"], reverse=True)
    assert ranked[0][1].ref == "el:0.1.3"
    assert len(ranked) == 2


def test_score_candidate_high_confidence_clean_rename():
    from maya.storage.models import HealingCandidate

    original = _el("el:0.0", "button", "Count: 0", path_fingerprint="abc")
    candidate_el = _el("el:0.0", "button", "Count: 0", data_testid="counter-button-v2", path_fingerprint="abc")
    candidate = HealingCandidate(
        strategy="test_id", value="counter-button-v2", confidence=0.0, signal_breakdown={"attribute": 1.0}
    )
    scored = score_candidate(candidate, original, candidate_el, tier_candidate_count=1, recent_snapshots=[])
    assert scored.confidence >= 0.90


def test_score_candidate_low_confidence_ambiguous_no_context():
    from maya.storage.models import HealingCandidate

    candidate = HealingCandidate(
        strategy="role", value="button", confidence=0.0, signal_breakdown={"attribute": 0.4}
    )
    scored = score_candidate(candidate, None, None, tier_candidate_count=5, recent_snapshots=[])
    assert scored.confidence < 0.90


def test_tier6_vision_llm_parses_json_response():
    class _StubLLM:
        def generate(self, prompt, images=None, tools=None, task_role=None):
            assert tools is None
            return LLMResponse(
                text='Sure, here it is: {"strategy": "text", "value": "Count: 0", "confidence": 0.7}',
                model="stub",
            )

    candidates = tier6_vision_llm(
        _StubLLM(), ax_tree="- button \"Count: 0\"", screenshot=b"\x00",
        original_el=None, original_locator=LocatorTarget(strategy="test_id", value="counter-button"),
    )
    assert len(candidates) == 1
    assert candidates[0].strategy == "text"
    assert candidates[0].value == "Count: 0"


def test_tier6_vision_llm_returns_empty_on_unparseable_response():
    class _StubLLM:
        def generate(self, prompt, images=None, tools=None, task_role=None):
            return LLMResponse(text="I cannot help with that.", model="stub")

    candidates = tier6_vision_llm(
        _StubLLM(), ax_tree="", screenshot=b"\x00",
        original_el=None, original_locator=LocatorTarget(strategy="test_id", value="x"),
    )
    assert candidates == []
