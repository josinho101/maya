from execution.validators.common_validator import CommonValidator


class GetValidator(CommonValidator):

    def validate(self, request_data, response_json, status_code, expected):

        validations = []
        overall = True

        overall &= self.validate_status_code(
            expected["status_code"], status_code, validations
        )

        if status_code == 200:

            if isinstance(response_json, list):

                if len(response_json) > 0:

                    first = response_json[0]

                    overall &= self.validate_required_fields(
                        first, expected["required_fields"], validations
                    )

                    overall &= self.validate_field_types(
                        first, expected["field_types"], validations
                    )

            elif isinstance(response_json, dict):

                overall &= self.validate_required_fields(
                    response_json, expected["required_fields"], validations
                )

                overall &= self.validate_field_types(
                    response_json, expected["field_types"], validations
                )

        return {"passed": bool(overall), "validation_details": validations}
