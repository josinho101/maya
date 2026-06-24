"""Assertion evaluation for the Execution Engine (F7-020), per plan.md §9's
MVP set — typed strategies guard against naive exact-match assertions breaking
on dynamic content. `numeric_range` and other typed strategies are deferred."""

from __future__ import annotations

import re
from typing import Any


def _equals(actual: Any, expected: Any) -> bool:
    return actual == expected


def _contains(actual: Any, expected: Any) -> bool:
    return expected in actual


def _not_empty(actual: Any, expected: Any) -> bool:
    return bool(actual)


def _regex_match(actual: Any, expected: Any) -> bool:
    return re.search(expected, actual) is not None


_ASSERTIONS: dict[str, Any] = {
    "equals": _equals,
    "contains": _contains,
    "not_empty": _not_empty,
    "regex_match": _regex_match,
}


def evaluate_assertion(assertion_type: str, actual: Any, expected: Any = None) -> bool:
    try:
        evaluator = _ASSERTIONS[assertion_type]
    except KeyError:
        raise ValueError(f"unknown assertion type: {assertion_type!r}") from None
    return evaluator(actual, expected)
