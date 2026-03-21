import time
import pathlib
from typing import Generator, Dict, Any, List
from .llm_base import BaseLLMClient
from volcenginesdkarkruntime import Ark
from volcenginesdkarkruntime.types.responses.response_reasoning_summary_text_delta_event import ResponseReasoningSummaryTextDeltaEvent
from volcenginesdkarkruntime.types.responses.response_text_delta_event import ResponseTextDeltaEvent

class VolcengineClient(BaseLLMClient):
    def _convert_history(self, messages: List[Dict[str, str]]) -> List[Dict[str, list[dict]]]:
        """将 OpenAI 格式历史转换为 Volcengine Ark 格式"""
        ark_history = []
        for msg in messages:
            if msg["role"] == "system":
                sys_prompt = msg["content"]
                ark_history.append({"role": "system", "content": [{"type": "input_text", "text": sys_prompt}]})
                continue
            role = "user" if msg["role"] == "user" else "assistant"
            ark_history.append({"role": role, "content": [{"type": "input_text", "text": str(msg['content'])}]})
        return ark_history

    def chat_stream(self, messages: List[Dict[str, Any]], temperature: float, image_paths: List[str] = None, **kwargs) -> Generator[Dict[str, Any], None, None]:
        client = Ark(base_url=self.base_url, api_key=self.api_key)

        reasoning_effort = kwargs.get("reasoningEffort", "medium")
        enable_search = kwargs.get("enable_search", False)
        keyWordsCountMapping = {"minimal": 2, "low": 4, "medium": 8, "high": 12}

        tools = [{
            "type": "web_search",
            "max_keyword": keyWordsCountMapping.get(reasoning_effort, 1)
        }] if enable_search else None

        req_messages = self._convert_history(messages)
        file_ids = []

        if image_paths:
            for i, img_path in enumerate(image_paths):
                yield {"type": "system", "content": f"正在上传图片 {i+1}/{len(image_paths)}: {img_path}...\n"}
                file = client.files.create(
                    file=open(img_path, "rb"),
                    purpose="user_data"
                )
                file_id = file.id
                file_ids.append(file_id)
                # 将上传的文件追加到最后一条用户消息的 content 中
                req_messages[-1]["content"].append({"type": "input_image", "file_id": file_id})

        response = client.responses.create(
            model = self.model_name,
            input=req_messages,
            temperature=temperature,
            stream=True,
            thinking={"type": "enabled"},
            tools=tools,
            reasoning={"effort": reasoning_effort}
        )

        begin_time = time.time()
        isThinking = False

        for event in response:
            if isinstance(event, ResponseReasoningSummaryTextDeltaEvent):
                isThinking = True
                yield {"type": "thinking", "content": event.delta}
            elif isinstance(event, ResponseTextDeltaEvent):
                if isThinking:
                    think_time = time.time() - begin_time
                    yield {"type": "meta", "thinking_time": think_time}
                    isThinking = False
                yield {"type": "content", "content": event.delta}
            else:
                continue

        try:
            for file_id in file_ids:
                client.files.delete(file_id=file_id)
        except Exception as e:
            yield {"type": "system", "content": f"未能删除上传的文件，可能会占用存储空间。错误详情: {e}"}

        client.close()