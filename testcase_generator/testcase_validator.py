from execution.validators.common_validator import CommonValidator
from testcase_generator.response_parser import LIFECYCLE_ROLES

ALLOWED_LIFECYCLE_ROLES = LIFECYCLE_ROLES | {"independent"}

_DICT_FIELDS = ("path_params", "query_params", "headers", "request_data", "files")


def validate_testcase(tc):
    """
    Validates a manually-authored or LLM-from-scenario test case against the
    schema TestcaseGenerator's LLM output already follows (see
    prompts/test_case_generation.md). Raises ValueError with a human-readable
    message on the first violation found. Does not touch tc_id/source/
    needs_review - those are always assigned by the caller, never trusted
    from client input.
    """

    if not isinstance(tc.get("test_scenario"), str) or not tc["test_scenario"].strip():
        raise ValueError("test_scenario must be a non-empty string")

    role = tc.get("lifecycle_role", "independent")
    if role not in ALLOWED_LIFECYCLE_ROLES:
        raise ValueError(
            f"lifecycle_role '{role}' is invalid - must be one of {sorted(ALLOWED_LIFECYCLE_ROLES)}"
        )

    for field in _DICT_FIELDS:
        value = tc.get(field, {})
        if not isinstance(value, dict):
            raise ValueError(f"{field} must be an object")

    expected_response = tc.get("expected_response")
    if not isinstance(expected_response, dict):
        raise ValueError("expected_response must be an object")

    status_code = expected_response.get("status_code")
    if not isinstance(status_code, int) or isinstance(status_code, bool):
        raise ValueError("expected_response.status_code must be an integer")

    required_fields = expected_response.get("required_fields", [])
    if not isinstance(required_fields, list) or not all(isinstance(f, str) for f in required_fields):
        raise ValueError("expected_response.required_fields must be a list of strings")

    field_types = expected_response.get("field_types", {})
    if not isinstance(field_types, dict):
        raise ValueError("expected_response.field_types must be an object")

    for field, type_name in field_types.items():
        if type_name not in CommonValidator.TYPE_MAP:
            raise ValueError(
                f"expected_response.field_types['{field}'] = '{type_name}' is not a "
                f"recognized type - must be one of {sorted(CommonValidator.TYPE_MAP)}"
            )


def demote_duplicate_lifecycle_role(tc, existing_test_cases):
    """
    If another test case in existing_test_cases already holds tc's
    lifecycle_role (and that role isn't "independent"), demotes tc's role to
    "independent" - mirrors response_parser._normalize_lifecycle_roles so the
    create/read/update/delete-is-unique-per-endpoint invariant
    _add_lifecycle_verification_test_cases depends on still holds after a
    manual/scenario addition.
    """

    role = tc.get("lifecycle_role", "independent")

    if role == "independent":
        return

    for existing in existing_test_cases:
        if existing.get("lifecycle_role") == role:
            tc["lifecycle_role"] = "independent"
            return
