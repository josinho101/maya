from configs.settings import LLM


class LLMClient:

    @staticmethod
    def get_llm_client():

        connector = LLM["connector"].lower()

        if connector == "ollama":

            from llm.connectors.ollama import OllamaLLM

            return OllamaLLM()

        else:

            raise ValueError(f"Unsupported LLM connector: {connector}")
