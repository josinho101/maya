import json
import yaml
import requests
from pathlib import Path


class SourceLoader:

    @staticmethod
    def load(source):

        if Path(source).exists():

            with open(source, "r", encoding="utf-8") as file:

                if source.endswith((".yaml", ".yml")):
                    return yaml.safe_load(file)

                return json.load(file)

        try:
            response = requests.get(source, timeout=10)

            response.raise_for_status()

        except requests.exceptions.ConnectionError as e:
            raise RuntimeError(
                f"Unable to connect to '{source}'. "
                f"Please verify that the server is running and the URL is accessible."
            ) from e

        except requests.exceptions.Timeout as e:
            raise RuntimeError(f"Request to '{source}' timed out.") from e

        except requests.exceptions.HTTPError as e:
            raise RuntimeError(
                f"HTTP error while accessing '{source}': "
                f"{e.response.status_code} {e.response.reason}"
            ) from e

        except requests.exceptions.RequestException as e:
            raise RuntimeError(
                f"Failed to load content from '{source}': {str(e)}"
            ) from e

        try:
            return response.json()

        except ValueError:
            return yaml.safe_load(response.text)
