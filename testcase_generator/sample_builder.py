_TYPE_DEFAULTS = {
    "string": "",
    "integer": 0,
    "number": 0,
    "boolean": False,
    "array": [],
    "object": {},
}


def _sample_value(schema):
    if not isinstance(schema, dict):
        return ""

    if "example" in schema:
        return schema["example"]

    if "default" in schema:
        return schema["default"]

    return _TYPE_DEFAULTS.get(schema.get("type"), "")


def _is_file_field(prop_schema):
    return (
        isinstance(prop_schema, dict)
        and prop_schema.get("type") == "string"
        and prop_schema.get("format") == "binary"
    )


def build_sample_testcase(api_details):
    """
    Deterministic, schema-grounded test case skeleton for the manual-add
    dialog - no LLM call. Mirrors the "realistic sample values based on
    datatype" instruction _shared_rules.md gives the LLM, done locally so the
    add dialog never opens on a blank form.
    """

    path_params = {}
    query_params = {}

    for param in api_details.get("parameters", []):
        name = param.get("name")
        if not name:
            continue
        value = _sample_value(param.get("schema", {}))
        if param.get("in") == "path":
            path_params[name] = value
        elif param.get("in") == "query":
            query_params[name] = value

    request_schema = api_details.get("request_schema") or {}
    request_properties = request_schema.get("properties", {})

    request_data = {}
    file_fields = []

    for name, prop_schema in request_properties.items():
        if _is_file_field(prop_schema):
            file_fields.append(name)
        else:
            request_data[name] = _sample_value(prop_schema)

    response_descriptions = api_details.get("response_descriptions", {})
    status_code = 200
    for code in sorted(response_descriptions):
        if code.startswith("2"):
            try:
                status_code = int(code)
            except ValueError:
                continue
            break

    response_schema = api_details.get("response_schema") or {}
    response_properties = response_schema.get("properties", {})
    required_fields = response_schema.get("required", [])

    field_types = {
        name: response_properties.get(name, {}).get("type", "string")
        for name in required_fields
        if name in response_properties
    }

    sample = {
        "test_scenario": "",
        "lifecycle_role": "independent",
        "path_params": path_params,
        "query_params": query_params,
        "headers": dict(api_details.get("headers", {})),
        "request_data": request_data,
        "files": {},
        "expected_response": {
            "status_code": status_code,
            "required_fields": list(required_fields),
            "field_types": field_types,
        },
    }

    return sample, file_fields
