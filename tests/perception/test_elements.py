from __future__ import annotations

from maya.perception.elements import extract_elements

AX_TREE = """\
- main:
  - 'button "Count: 0"'
  - button "Settings"
"""

DOM_HTML = """\
<html><body>
  <main>
    <button id="counter" type="button" data-testid="counter-button">Count: 0</button>
    <button id="reveal-panel" type="button" data-testid="reveal-panel-button">Settings</button>
  </main>
</body></html>
"""


def test_extract_elements_populates_expected_fields():
    elements = extract_elements(AX_TREE, DOM_HTML)
    roles = {(e.role, e.name) for e in elements}
    assert ("main", None) in roles
    assert ("button", "Count: 0") in roles
    assert ("button", "Settings") in roles

    counter = next(e for e in elements if e.name == "Count: 0")
    assert counter.role == "button"
    assert counter.data_testid == "counter-button"
    assert counter.ref
    assert counter.path_fingerprint

    settings = next(e for e in elements if e.name == "Settings")
    assert settings.data_testid == "reveal-panel-button"


def test_extract_elements_no_testid_when_dom_has_none():
    elements = extract_elements(AX_TREE, "<html><body></body></html>")
    assert all(e.data_testid is None for e in elements)


def test_extract_elements_path_fingerprint_stable_across_text_change():
    renamed_dom = DOM_HTML.replace("Count: 0", "Count: 5")
    renamed_ax = AX_TREE.replace('Count: 0', 'Count: 5')

    before = extract_elements(AX_TREE, DOM_HTML)
    after = extract_elements(renamed_ax, renamed_dom)

    before_counter = next(e for e in before if e.data_testid == "counter-button")
    after_counter = next(e for e in after if e.data_testid == "counter-button")
    assert before_counter.path_fingerprint == after_counter.path_fingerprint
    assert before_counter.name != after_counter.name
