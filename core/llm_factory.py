from .llm_openai import OpenAICompatibleClient
from .llm_gemini import GeminiClient
from .llm_base import BaseLLMClient
from .llm_doubao import VolcengineClient
from .llm_qwen import QwenClient
from .llm_default import DefaultClient

class LLMFactory:
    @staticmethod
    def create_client(model_name: str, keys: dict, type: str = None) -> BaseLLMClient:
        if "gemini" in model_name:
            return GeminiClient(api_key=keys["gemini"], model_name=model_name)
        elif "qwen" in model_name:
            return QwenClient(api_key=keys["qwen"], model_name=model_name, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
        elif "doubao" in model_name:
            return VolcengineClient(api_key=keys["doubao"], model_name=model_name, base_url="https://ark.cn-beijing.volces.com/api/v3")
        elif "deepseek" in model_name:
            return OpenAICompatibleClient(api_key=keys["deepseek"], model_name=model_name, base_url="https://api.deepseek.com")
        else:
            return DefaultClient(api_key="", model_name=model_name, base_url=type)  # base_url 这里我们暂时用来传递模型类型