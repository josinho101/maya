from execution.validators.get_validator import GetValidator
from execution.validators.post_validator import PostValidator
from execution.validators.put_validator import PutValidator
from execution.validators.patch_validator import PatchValidator
from execution.validators.delete_validator import DeleteValidator


class ValidatorFactory:

    @staticmethod
    def get_validator(method):

        method = method.upper()

        if method == "GET":
            return GetValidator()

        if method == "POST":
            return PostValidator()

        if method == "PUT":
            return PutValidator()

        if method == "PATCH":
            return PatchValidator()

        if method == "DELETE":
            return DeleteValidator()

        return GetValidator()
