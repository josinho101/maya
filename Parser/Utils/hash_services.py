import hashlib
import json


class HashService:

    @staticmethod
    def generate_api_sha(endpoint, method, details):

        payload = {"endpoint": endpoint, "method": method.upper(), "details": details}

        return hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()
