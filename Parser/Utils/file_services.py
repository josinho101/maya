import json
import os


class FileService:

    @staticmethod
    def load_existing_output(output_file):

        try:

            with open(output_file, "r", encoding="utf-8") as file:

                content = file.read().strip()

                if not content:

                    return {"project": {}, "apis": []}

                return json.loads(content)

        except (FileNotFoundError, json.JSONDecodeError):

            return {"project": {}, "apis": []}

    # output
    # student
    # metadata
    @staticmethod
    def save_output(output_file, data):

        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as file:

            json.dump(data, file, indent=2, ensure_ascii=False)
