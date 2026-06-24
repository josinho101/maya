from __future__ import annotations

import pytest

from maya.engines.assertions import evaluate_assertion


def test_equals():
    assert evaluate_assertion("equals", "Count: 1", "Count: 1")
    assert not evaluate_assertion("equals", "Count: 1", "Count: 2")


def test_contains():
    assert evaluate_assertion("contains", "<button>Count: 1</button>", "Count: 1")
    assert not evaluate_assertion("contains", "<button>Count: 1</button>", "Count: 2")


def test_not_empty():
    assert evaluate_assertion("not_empty", "some text")
    assert not evaluate_assertion("not_empty", "")


def test_regex_match():
    assert evaluate_assertion("regex_match", "Count: 42", r"Count: \d+")
    assert not evaluate_assertion("regex_match", "Count: abc", r"Count: \d+")


def test_unknown_assertion_type_raises():
    with pytest.raises(ValueError):
        evaluate_assertion("numeric_range", "5", None)
