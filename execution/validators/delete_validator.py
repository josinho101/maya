from execution.validators.common_validator import CommonValidator


class DeleteValidator(CommonValidator):

    def validate(self, request_data, response_json, status_code, expected):

        validations = []
        overall = True

        overall &= self.validate_status_code(
            expected["status_code"], status_code, validations
        )

        return {"passed": bool(overall), "validation_details": validations}
