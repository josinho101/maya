import re

_TRAILING_PARAM = re.compile(r"/\{[^/]+\}$")

LIFECYCLE_ROLES = ("create", "read", "update", "delete")
VERIFICATION_ROLES = ("verify_create", "verify_update", "verify_delete")


def resource_key_for(endpoint):
    """
    Derives a resource grouping key from an endpoint path by stripping a
    single trailing path-parameter segment, e.g. "/pet/{petId}" and "/pet"
    both map to "/pet". Endpoints with no trailing path parameter (or with
    parameters earlier in the path) keep their own endpoint as the key.
    """

    return _TRAILING_PARAM.sub("", endpoint) or endpoint


def group_by_resource(results):
    """
    Groups endpoint result entries (as found in generated_testcases.json's
    "results" list) by resource_key_for(endpoint).

    Returns: dict[str, list[result_entry]]
    """

    groups = {}

    for result in results:

        endpoint = result.get("endpoint", "")

        key = resource_key_for(endpoint)

        groups.setdefault(key, []).append(result)

    return groups


def find_lifecycle_test_cases(group_entries):
    """
    Scans a resource group's result entries for the (at most one per role)
    test case tagged "create"/"read"/"update"/"delete".

    Returns: dict[role, (entry, tc)]
    """

    lifecycle_map = {}

    for entry in group_entries:

        for tc in entry.get("test_cases", []):

            role = tc.get("lifecycle_role")

            if role in LIFECYCLE_ROLES and role not in lifecycle_map:
                lifecycle_map[role] = (entry, tc)

    return lifecycle_map


def find_single_resource_entry(group_entries, key, method):
    """
    Finds the result entry in a resource group whose endpoint represents the
    single-resource operation (i.e. has the trailing path-parameter segment
    that group_by_resource() stripped to produce `key`) for the given HTTP
    method.

    Returns: the entry, or None if no such endpoint exists in the group.
    """

    for entry in group_entries:

        if entry.get("endpoint") != key and entry.get("method", "").upper() == method:
            return entry

    return None


def find_verification_test_cases(group_entries):
    """
    Scans a resource group's result entries for the (at most one per role)
    test case tagged "verify_create"/"verify_update"/"verify_delete" - the
    persisted CRUD-consistency checks generated alongside the create/read/
    update/delete test cases.

    Returns: dict[role, (entry, tc)]
    """

    verification_map = {}

    for entry in group_entries:

        for tc in entry.get("test_cases", []):

            role = tc.get("lifecycle_role")

            if role in VERIFICATION_ROLES and role not in verification_map:
                verification_map[role] = (entry, tc)

    return verification_map
