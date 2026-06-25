class RequestBuilder:

    @staticmethod
    def build_url(base_url, endpoint, path_params):

        final_url = endpoint

        for key, value in path_params.items():

            final_url = final_url.replace("{" + key + "}", str(value))

        return base_url + final_url
