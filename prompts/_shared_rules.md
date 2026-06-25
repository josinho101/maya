RESPONSE RULES:

1. Return a single valid JSON object only.
2. Do not return:
   * Markdown
   * Explanations
   * Notes
   * Code blocks
   * Additional text
   * string concatenation ("a" + "b")

3. Root response must be a JSON object.
4. No duplicate test cases.
5. Do not mention test case category names in test_scenario.
6. Every test case must contain:
   * test_scenario
   * lifecycle_role
   * expected_response.status_code
7. Always generate realistic sample values based on datatype.
8. Do not generate JavaScript expressions, functions, variables, or code snippets.

Example:

INVALID:
"A".repeat(1000)

VALID:
"AAAAAAAAAAAA"

INPUT APPLICABILITY RULES:

Generate test cases only for inputs explicitly defined in API Details.

Do NOT invent:

* path parameters
* query parameters
* headers
* request body fields
* file uploads

If an input section does not exist in API Details:

* Do not generate test cases for that section.
* Return an empty object {} for the corresponding section.

Examples:

"path_params": {}
"query_params": {}
"headers": {}
"request_data": {}
"files": {}

PATH PARAMETER RULES:

Generate path_params only when path parameters are explicitly present.

Example:

Endpoint:
/pets/{petId}

Generate:

"path_params":
{
  "petId": 1001
}

If path parameters are not defined, do not create them.

QUERY PARAMETER RULES:

Generate query_params only when query parameters are explicitly present.

Example:

"query_params":
{
  "status": "available"
}

If query parameters are not defined, do not create them.

FILE UPLOAD RULES:

If request contains file-type fields:

* Do NOT place them inside request_data.
* Place them inside files.

Example:

"files":
{
  "file": "image.jpg"
}

Only generate files when file fields are explicitly defined.

REQUEST BODY RULES:

request_data must contain only body/form fields.

Do not place:

* files
* path parameters
* query parameters
* headers

inside request_data.

RESOURCE DEPENDENCY RULES:

The execution framework may execute APIs as part of a CRUD workflow.

When an endpoint contains path parameters, determine whether the parameter represents a resource identifier created by another API.

Examples:

Creation API:

POST /users .


Dependent APIs:

GET /users/{id}
PUT /users/{id}
PATCH /users/{id}
DELETE /users/{id}

Generate:

"path_params":
{
  "id": "{LAST_CREATED_RESOURCE.id}"
}

Similarly:

POST /pets

GET /pets/{petId}

Generate:

{
  "petId": "{LAST_CREATED_RESOURCE.petId}"
}


Apply this rule whenever:

1. Endpoint contains path parameters.
2. Scenario requires an existing resource.
3. Parameter logically represents the created resource.

DO NOT USE PLACEHOLDERS FOR:

* invalid ids
* empty ids
* malformed ids
* non-existent ids
* boundary test values

Generate independent values for such scenarios.

IMPORTANT:

The execution framework automatically replaces:

{LAST_CREATED_RESOURCE.<field>}

with actual runtime values.


For positive scenarios of GET/PUT/PATCH/DELETE methods that require an existing resource, never generate fixed values such as:"user123", "12345","pet001".Always use the placeholder.


RESPONSE VALIDATION RULES:

Validation must be generated strictly from response_schema.

Mapping Rules:

response_schema.properties keys
→ required_fields

response_schema.properties.type
→ field_types

Example:

{
  "properties": {
    "id": {
      "type": "string"
    },
    "name": {
      "type": "string"
    }
  }
}

Must generate:

"required_fields":
[
  "id",
  "name"
]

"field_types":
{
  "id": "string",
  "name": "string"
}

ARRAY RESPONSE RULES:

If:

response_schema.type = "array"

then:

required_fields must be derived from:

items.properties

field_types must be derived from:

items.properties.<field>.type

STRICT SCHEMA RULES:

If response_schema exists AND expected_response.status_code is a 2xx success code:

* required_fields must not be empty.
* field_types must not be empty.
* Do not guess fields.
* Do not infer fields.
* Derive everything directly from schema.

For negative/error test cases (any non-2xx status_code), the documented response_schema does not apply:

* required_fields must be an empty array [].
* field_types must be an empty object {}.

OUTPUT FORMAT:

{
  "endpoint": "",
  "method": "",
  "test_cases": [
    {
      "test_scenario": "",
      "lifecycle_role": "independent",
      "path_params": {},
      "query_params": {},
      "headers": {},
      "request_data": {},
      "files": {},
      "expected_response": {
        "status_code": 200,
        "required_fields": [],
        "field_types": {}
      }
    }
  ]
}
