from typing import Dict, Generator, List
import json
import time
from .llm_base import BaseLLMClient

class DefaultClient(BaseLLMClient):
    def chat_stream(self, messages: List[Dict[str, str]], temperature: float, **kwargs) -> Generator[Dict[str, str], None, None]:
        if self.model_name == "自己回答":
            yield {"type": "input"}
