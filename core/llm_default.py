from typing import Dict, Generator, List
import json
import time
from .llm_base import BaseLLMClient

class DefaultModelChoise(Exception):
    pass

class DefaultClient(BaseLLMClient):
    def chat_stream(self, messages: List[Dict[str, str]], temperature: float, **kwargs) -> Generator[Dict[str, str], None, None]:
        if self.model_name == "自己回答":
            yield {"type": "input"}
        elif self.model_name == "错误消息":
            yield {"type": "error_msg"}

        elif self.model_name == "default":
            raise DefaultModelChoise("这里选择default，直接抛出一个异常用来开启新的对话轮次")
