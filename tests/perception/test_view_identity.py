from __future__ import annotations

from maya.perception.view_identity import heading_signal, structural_fingerprint

FLAT_TREE = """\
- text: Username
- textbox "Username"
- text: Password
- textbox "Password"
- button "Log in"
"""

FLAT_TREE_RENAMED = """\
- text: Email
- textbox "Email"
- text: Passphrase
- textbox "Passphrase"
- button "Sign in"
"""

LANDMARK_TREE = """\
- main:
  - heading "Welcome" [level=1]
  - paragraph: Some text here
  - region "Sidebar":
    - button "Click"
"""

NESTED_DIALOG_TREE = """\
- main:
  - heading "Welcome" [level=1]
- dialog "Settings":
  - heading "Settings" [level=2]
"""


def test_structural_fingerprint_ignores_text_differences():
    assert structural_fingerprint(FLAT_TREE) == structural_fingerprint(FLAT_TREE_RENAMED)


def test_structural_fingerprint_differs_for_distinct_landmark_shape():
    assert structural_fingerprint(LANDMARK_TREE) != structural_fingerprint(NESTED_DIALOG_TREE)
    assert structural_fingerprint(FLAT_TREE) != structural_fingerprint(LANDMARK_TREE)


def test_heading_signal_prefers_ax_tree_heading():
    assert heading_signal(LANDMARK_TREE, "<title>Ignored</title>") == "Welcome"


def test_heading_signal_falls_back_to_dom_title():
    dom_html = "<html><head><title>MAYA Demo App</title></head></html>"
    assert heading_signal(FLAT_TREE, dom_html) == "MAYA Demo App"


def test_heading_signal_empty_when_neither_present():
    assert heading_signal(FLAT_TREE, "<html></html>") == ""
