from Parser.swagger.schema_parser import SchemaParser


class ParameterParser:

    PARAMETER_METADATA_FIELDS = [
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
        "writeOnly"
    ]

    def __init__(self, source_data):

        self.source_data = source_data

        self.schema_parser = SchemaParser(source_data)

    def parse_parameters(self, parameters):

        parsed_parameters = []

        request_body_schema = {}

        for param in parameters:

            param_location = param.get("in")

            #
            # Swagger 2.0 body parameter
            #
            if param_location == "body":

                body_schema = param.get("schema", {})

                request_body_schema = self.schema_parser.parse_schema(
                    body_schema
                )

            else:

                #
                # OpenAPI 3 parameter schema
                #
                schema_data = param.get("schema", {})

                #
                # Swagger 2 parameter definition
                #
                if not schema_data:

                    schema_data = {
                        "type": param.get("type", "string")
                    }

                    for field in self.PARAMETER_METADATA_FIELDS:

                        value = param.get(field)

                        if value not in (None, "", [], {}, ()):

                            schema_data[field] = value

                parsed_parameter = {
                    "name": param.get("name"),
                    "in": param_location,
                    "required": param.get("required", False),
                    "schema": self.schema_parser.parse_schema(
                        schema_data
                    ),
                }

                parsed_parameters.append(
                    parsed_parameter
                )

        return parsed_parameters, request_body_schema

    def parse_request_body(self, details):

        request_body_schema = {}

        request_body = details.get("requestBody", {})

        content = request_body.get("content", {})

        for media_type, media_details in content.items():

            schema = media_details.get("schema", {})

            request_body_schema = self.schema_parser.parse_schema(
                schema
            )

            break

        return request_body_schema

    def generate_acceptance_criteria(
        self,
        parameters,
        request_body_schema
    ):

        criteria = []

        for parameter in parameters:

            name = parameter.get("name")

            schema = parameter.get("schema", {})

            param_type = schema.get(
                "type",
                "string"
            )

            criteria.append(
                f"{name} should be of type {param_type}"
            )

        if request_body_schema.get("type") == "object":

            properties = request_body_schema.get(
                "properties",
                {}
            )

            for field, details in properties.items():

                field_type = details.get(
                    "type",
                    "string"
                )

                criteria.append(
                    f"{field} should be of type {field_type}"
                )

        elif request_body_schema.get("type") == "array":

            item_schema = request_body_schema.get(
                "items",
                {}
            )

            properties = item_schema.get(
                "properties",
                {}
            )

            for field, details in properties.items():

                field_type = details.get(
                    "type",
                    "string"
                )

                criteria.append(
                    f"{field} should be of type {field_type}"
                )

        return criteria
# from Parser.swagger.schema_parser import SchemaParser


# class ParameterParser:

#     def __init__(self, source_data):

#         self.source_data = source_data

#         self.schema_parser = SchemaParser(source_data)

#     def parse_parameters(self, parameters):

#         parsed_parameters = []

#         request_body_schema = {}

#         for param in parameters:

#             param_location = param.get("in")

#             if param_location == "body":

#                 body_schema = param.get("schema", {})

#                 request_body_schema = self.schema_parser.parse_schema(body_schema)

#             else:

#                 schema_data = param.get("schema", {})

#                 if not schema_data:

#                     schema_data = {"type": param.get("type", "string")}

#                     if param.get("format"):

#                         schema_data["format"] = param.get("format")

#                     if param.get("enum"):

#                         schema_data["enum"] = param.get("enum")

#                 parameter_object = {
#                     "name": param.get("name"),
#                     "in": param_location,
#                     "schema": (self.schema_parser.parse_schema(schema_data)),
#                 }

#                 parsed_parameters.append(parameter_object)

#         return (parsed_parameters, request_body_schema)

#     def parse_request_body(self, details):

#         request_body_schema = {}

#         request_body = details.get("requestBody", {})

#         content = request_body.get("content", {})

#         for media_type, media_details in content.items():

#             schema = media_details.get("schema", {})

#             request_body_schema = self.schema_parser.parse_schema(schema)

#             break

#         return request_body_schema

#     def generate_acceptance_criteria(self, parameters, request_body_schema):

#         criteria = []

#         for parameter in parameters:

#             name = parameter.get("name")

#             schema = parameter.get("schema", {})

#             param_type = schema.get("type", "string")

#             criteria.append(f"{name} should be of type {param_type}")

#         if request_body_schema.get("type") == "object":

#             properties = request_body_schema.get("properties", {})

#             for field, details in properties.items():

#                 field_type = details.get("type", "string")

#                 criteria.append(f"{field} should be of type {field_type}")

#         elif request_body_schema.get("type") == "array":

#             item_schema = request_body_schema.get("items", {})

#             properties = item_schema.get("properties", {})

#             for field, details in properties.items():

#                 field_type = details.get("type", "string")

#                 criteria.append(f"{field} should be of type {field_type}")

#         return criteria
