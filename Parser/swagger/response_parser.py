from Parser.swagger.schema_parser import SchemaParser


class ResponseParser:

    def __init__(self, source_data):

        self.source_data = source_data

        self.schema_parser = SchemaParser(source_data)

    def parse_response_schema(self, responses):

        success_response = None

        for status_code, response in responses.items():

            if str(status_code).startswith("2"):

                success_response = response

                break

        if not success_response:

            success_response = responses.get("default")

        if not success_response:

            return {"type": "unknown", "note": "Response schema not documented"}

        if "schema" in success_response:

            schema = success_response.get("schema", {})

            parsed_schema = self.schema_parser.parse_schema(schema)

            if parsed_schema:

                return parsed_schema

        content = success_response.get("content", {})

        if content:

            for media_type, media_details in content.items():

                schema = media_details.get("schema", {})

                parsed_schema = self.schema_parser.parse_schema(schema)

                if parsed_schema:

                    return parsed_schema

        return {
            "type": "unknown",
            "description": success_response.get("description", ""),
            "note": "Response schema not documented",
        }
