import json

from llm.core.exceptions import LLMResponseError

LIFECYCLE_ROLES = {"create", "read", "update", "delete"}


def parse_response(response):

    cleaned = _strip_markdown_fences(response)

    try:
        parsed = json.loads(cleaned)

    except json.JSONDecodeError as e:

        raise LLMResponseError(
            f"Malformed JSON response from LLM:\n{e}\n\nRAW RESPONSE:\n{response}"
        )

    _normalize_lifecycle_roles(parsed)

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
