from abc import ABC, abstractmethod
from typing import Generator, Dict, Any, List

class BaseLLMClient(ABC):
    def __init__(self, api_key: str, model_name: str, base_url: str = ""):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url

    @abstractmethod
    def chat_stream(self, messages: List[Dict[str, str]], temperature: float, **kwargs) -> Generator[Dict[str, Any], None, None]:
        """
        统一的流式输出接口。
        必须 yield 包含具体信息的字典，例如：
        {"type": "thinking", "content": "思考过程片段..."}
        {"type": "content", "content": "正式回答片段..."}
        {"type": "meta", "thinking_time": 12.5}
        """
        pass