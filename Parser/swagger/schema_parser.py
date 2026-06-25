class SchemaParser:

    METADATA_FIELDS = [
        "format",
        "enum",
        "default",
        "example",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        "minLength",
        "maxLength",
        "pattern",
        "minItems",
        "maxItems",
        "nullable",
        "readOnly",
        "writeOnly",
        "additionalProperties",
    ]

    def __init__(self, source_data):

        self.source_data = source_data

    def resolve_ref(self, schema_ref):

        if "$ref" not in schema_ref:
            return schema_ref

        ref_path = schema_ref["$ref"]

        current = self.source_data

        for part in ref_path[2:].split("/"):
            current = current.get(part, {})

        return current

    def _copy_metadata(self, source, target):

        for field in self.METADATA_FIELDS:

            value = source.get(field)

            # Skip only truly empty values.
            # Keep valid values like 0 and False.
            if value not in (None, "", [], {}, ()):
                target[field] = value

        return target

    def parse_schema(self, schema):

        if not schema:
            return {}

        #
        # Resolve references
        #
        if "$ref" in schema:
            schema = self.resolve_ref(schema)

        #
        # Handle allOf
        #
        if "allOf" in schema:

            merged = {
                "type": "object",
                "required": [],
                "properties": {}
            }

            for item in schema["allOf"]:

                parsed = self.parse_schema(item)

                if parsed.get("type") == "object":

                    merged["properties"].update(
                        parsed.get("properties", {})
                    )

                    merged["required"].extend(
                        parsed.get("required", [])
                    )

            merged["required"] = list(
                dict.fromkeys(merged["required"])
            )

            return self._copy_metadata(schema, merged)

        #
        # Handle oneOf
        #
        if "oneOf" in schema:
            return self.parse_schema(schema["oneOf"][0])

        #
        # Handle anyOf
        #
        if "anyOf" in schema:
            return self.parse_schema(schema["anyOf"][0])

        schema_type = schema.get("type")

        #
        # Object
        #
        if schema_type == "object" or "properties" in schema:

            result = {
                "type": "object",
                "required": schema.get("required", []),
                "properties": {
                    key: self.parse_schema(value)
                    for key, value in schema.get(
                        "properties", {}
                    ).items()
                }
            }

            return self._copy_metadata(schema, result)

        #
        # Array
        #
        if schema_type == "array":

            result = {
                "type": "array",
                "items": self.parse_schema(
                    schema.get("items", {})
                )
            }

            return self._copy_metadata(schema, result)

        #
        # Primitive types
        #
        result = {
            "type": schema.get("type", "string")
        }

        return self._copy_metadata(schema, result)

# class SchemaParser:

#     def __init__(self, source_data):
#         self.source_data = source_data

#     def resolve_ref(self, schema_ref):

#         if "$ref" not in schema_ref:
#             return schema_ref

#         ref_path = schema_ref["$ref"]

#         current = self.source_data

#         for part in ref_path[2:].split("/"):
#             current = current.get(part, {})

#         return current

#     def parse_schema(self, schema):

#         if not schema:
#             return {}

#         if "$ref" in schema:
#             schema = self.resolve_ref(schema)

#         schema_type = schema.get("type")

#         if schema_type == "object" or "properties" in schema:
#             return {
#                 "type": "object",
#                 "required": schema.get("required", []),
#                 "properties": {
#                     key: self.parse_schema(value)
#                     for key, value in schema.get("properties", {}).items()
#                 },
#             }

#         if schema_type == "array":
#             result = {
#                 "type": "array",
#                 "items": self.parse_schema(schema.get("items", {})),
#             }

#             for field in ["minItems", "maxItems", "uniqueItems", "default"]:
#                 if field in schema:
#                     result[field] = schema[field]

#             return result

#         result = {
#             "type": schema.get("type", "string")
#         }

#         metadata_fields = [
#             "format",
#             "enum",
#             "default",
#             "example",
#             "minimum",
#             "maximum",
#             "exclusiveMinimum",
#             "exclusiveMaximum",
#             "multipleOf",
#             "minLength",
#             "maxLength",
#             "pattern",
#             "minItems",
#             "maxItems",
#             "nullable",
#             "readOnly",
#             "writeOnly",
#             "description"
#         ]
#         for field in metadata_fields:
#             value = schema.get(field)

#             if value not in (None, "", [], {}):
#                 result[field] = value
#         # for field in metadata_fields:
#         #     if field in schema:
#         #         result[field] = schema[field]

#         return result

