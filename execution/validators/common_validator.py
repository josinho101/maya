class CommonValidator:

    TYPE_MAP = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    def validate_status_code(self, expected, actual, validations):

        passed = expected == actual
        validations.append(
            {
                "check": "status_code",
                "expected": expected,
                "actual": actual,
                "passed": passed,
            }
        )
        return passed

    def validate_required_fields(self, target, required_fields, validations):

        result = True

        for field in required_fields:

            exists = field in target

            validations.append({"check": f"field_exists:{field}", "passed": exists})

            if not exists:
                result = False

        return result

    def validate_field_types(self, target, field_types, validations, required_fields=None):

        required_fields = required_fields or []

        result = True

        for field, expected_type in field_types.items():

            value = target.get(field)

            if value is None and field not in required_fields:

                validations.append(
                    {
                        "check": f"type:{field}",
                        "expected": expected_type,
                        "actual": "NoneType",
                        "passed": True,
                    }
                )

                continue

            expected_python_type = self.TYPE_MAP.get(expected_type)

            passed = isinstance(value, expected_python_type)

            validations.append(
                {
                    "check": f"type:{field}",
                    "expected": expected_type,
                    "actual": type(value).__name__,
                    "passed": passed,
                }
            )

            if not passed:
                result = False

        return result
