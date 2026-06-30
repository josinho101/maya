import json

from llm.core.exceptions import LLMResponseError
from Utils.logger import logger

LIFECYCLE_ROLES = {"create", "read", "update", "delete"}


def parse_response(response, requires_auth=False):

    cleaned = _strip_markdown_fences(response)

    try:
        parsed = json.loads(cleaned)

    except json.JSONDecodeError as e:

        raise LLMResponseError(
            f"Malformed JSON response from LLM:\n{e}\n\nRAW RESPONSE:\n{response}"
        )

    _normalize_lifecycle_roles(parsed)

    normalize_auth_overrides(parsed, requires_auth)

    return parsed


def _strip_markdown_fences(response):
    """
    Some models wrap JSON output in ```json ... ``` fences despite being
    told not to. Strip them so a well-formed response isn't misdiagnosed
    as truncated/malformed.
    """

    text = response.strip()

    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.rstrip().endswith("```"):
            text = text.rstrip()[: -3]

    return text.strip()


def _normalize_lifecycle_roles(parsed_response):
    """
    Ensure every test case has a lifecycle_role, defaulting to "independent"
    when the model omits it, and demoting duplicate role assignments so at
    most one test case per endpoint carries a given non-independent role.
    """

    test_cases = parsed_response.get("test_cases", [])

    seen_roles = set()

    for tc in test_cases:

        role = tc.get("lifecycle_role")

        if role not in LIFECYCLE_ROLES:
            tc["lifecycle_role"] = "independent"
            continue

        if role in seen_roles:
            tc["lifecycle_role"] = "independent"
        else:
            seen_roles.add(role)


def normalize_auth_overrides(parsed_response, requires_auth):
    """
    Deterministically enforces the auth_override contract regardless of
    whether the LLM honored it: drops any auth_override test case for an
    endpoint that doesn't require auth, and caps surviving "missing"/
    "invalid" overrides to at most one each.
    """

    test_cases = parsed_response.get("test_cases", [])

    if not requires_auth:

        kept = [tc for tc in test_cases if not tc.get("auth_override")]

        if len(kept) != len(test_cases):
            logger.warning(
                f"Endpoint does not require auth - dropped "
                f"{len(test_cases) - len(kept)} auth_override test case(s) "
                f"the LLM generated anyway."
            )

        parsed_response["test_cases"] = kept
        return

    seen_overrides = set()

    for tc in test_cases:

        override = tc.get("auth_override")

        if override not in ("missing", "invalid"):
            continue

        if override in seen_overrides:
            tc["auth_override"] = None
        else:
            seen_overrides.add(override)
