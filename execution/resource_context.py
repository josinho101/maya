class ResourceContext:

    _resources = {}

    @classmethod
    def store(cls, resource_key, response_json):

        if isinstance(response_json, dict):
            cls._resources[resource_key] = response_json

    @classmethod
    def get(cls, resource_key):

        return cls._resources.get(resource_key, {})

    @classmethod
    def resolve(cls, resource_key, data):

        resource = cls._resources.get(resource_key, {})

        return cls._resolve_value(data, resource)

    @classmethod
    def _resolve_value(cls, data, resource):

        if isinstance(data, dict):

            resolved = {}

            for key, value in data.items():
                resolved[key] = cls._resolve_value(value, resource)

            return resolved

        elif isinstance(data, list):

            return [cls._resolve_value(item, resource) for item in data]

        elif isinstance(data, str):

            if data.startswith("{LAST_CREATED_RESOURCE.") and data.endswith("}"):

                field = data.replace("{LAST_CREATED_RESOURCE.", "").replace("}", "")

                return resource.get(field)

        return data
