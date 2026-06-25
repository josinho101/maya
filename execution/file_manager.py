import os


class FileManager:

    @staticmethod
    def get_files(files_data):

        files = {}

        for field_name, file_path in files_data.items():

            if not file_path:
                continue

            if not os.path.isfile(file_path):

                raise FileNotFoundError(f"File not found: {file_path}")

            files[field_name] = open(file_path, "rb")

        return files
