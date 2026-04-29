from .llm_openai import OpenAIClient
print("\r[S] 导入核心库 [1/5]", end="")
from .llm_gemini import GeminiClient
print("\r[S] 导入核心库 [2/5]", end="")
from .llm_base import BaseLLMClient
from .llm_doubao import VolcengineClient
print("\r[S] 导入核心库 [3/5]", end="")
from .llm_qwen import QwenClient
print("\r[S] 导入核心库 [4/5]", end="")
from .llm_anthropic import AnthropicLLMClient
print("\r[S] 导入核心库 [5/5]", end="")
from .llm_default import DefaultClient
from .multi_assistant import MultiAssistant
print("\r[S] 核心库导入完成！          ")

class LLMFactory:
    @staticmethod
    def create_client(model_name: str, keys: dict, type: str = None) -> BaseLLMClient:
        if "gemini" in model_name:
            return GeminiClient(api_key=keys["gemini"], model_name=model_name)
        elif "qwen" in model_name:
            return QwenClient(api_key=keys["qwen"], model_name=model_name, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
        elif "doubao" in model_name or model_name == "deepseek-v3-2-251201":
            return VolcengineClient(api_key=keys["doubao"], model_name=model_name, base_url="https://ark.cn-beijing.volces.com/api/v3")
        elif "deepseek" in model_name and model_name != "deepseek-v3-2-251201":
            return OpenAIClient(api_key=keys["deepseek"], model_name=model_name, base_url="https://api.deepseek.com")
        elif "kimi" in model_name:
            return OpenAIClient(api_key=keys["kimi"], model_name=model_name, base_url="https://api.moonshot.cn/v1")
        elif "minimax" in model_name.lower():
            return AnthropicLLMClient(api_key=keys["minimax"], model_name=model_name, base_url="https://api.minimaxi.com/anthropic")
        elif "multi-assistant" in model_name:
            multi_keys = {
                provider: keys.get(provider, "")
                for provider in ["deepseek", "qwen", "doubao", "kimi"]
                if keys.get(provider)
            }
            return MultiAssistant(
                api_keys=multi_keys,
                model_name=model_name,
                base_urls={
                    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "doubao": "https://ark.cn-beijing.volces.com/api/v3",
                    "deepseek": "https://api.deepseek.com",
                    "kimi": "https://api.moonshot.cn/v1"
                    })
        else:
            return DefaultClient(api_key="", model_name=model_name, base_url="")