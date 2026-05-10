import json
import time
from typing import Any, Dict, Generator, List

from volcenginesdkarkruntime import Ark
from volcenginesdkarkruntime.types.responses.response_reasoning_summary_text_delta_event import (
    ResponseReasoningSummaryTextDeltaEvent,
)
from volcenginesdkarkruntime.types.responses.response_text_delta_event import ResponseTextDeltaEvent

from .llm_base import BaseLLMClient


class VolcengineClient(BaseLLMClient):
    def _stringify_content(self, content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        try:
            return json.dumps(content, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(content)

    def _input_text_message(self, role: str, content: Any) -> Dict[str, Any]:
        return {
            "role": role,
            "content": [{"type": "input_text", "text": self._stringify_content(content)}],
        }

    def _convert_tool_calls(
        self,
        msg: Dict[str, Any],
        valid_call_ids: set[str] | None = None,
    ) -> List[Dict[str, str]]:
        converted_tool_calls: List[Dict[str, str]] = []
        raw_tool_calls = msg.get("tool_calls", [])
        if not isinstance(raw_tool_calls, list):
            return converted_tool_calls

        for tool_call in raw_tool_calls:
            if not isinstance(tool_call, dict):
                continue

            call_id = str(tool_call.get("id", "")).strip()
            function_info = tool_call.get("function", {})
            if not isinstance(function_info, dict):
                function_info = {}

            name = str(function_info.get("name") or tool_call.get("name") or "").strip()
            arguments = function_info.get("arguments", "{}")
            arguments_text = self._stringify_content(arguments).strip() or "{}"

            if not call_id or not name:
                continue
            if valid_call_ids is not None and call_id not in valid_call_ids:
                continue

            converted_tool_calls.append(
                {
                    "type": "function_call",
                    "call_id": call_id,
                    "name": name,
                    "arguments": arguments_text,
                }
            )

        return converted_tool_calls

    def _convert_tool_result(
        self,
        msg: Dict[str, Any],
        known_call_ids: set[str] | None = None,
    ) -> Dict[str, Any]:
        call_id = str(msg.get("tool_call_id", "")).strip()
        output = self._stringify_content(msg.get("content", ""))
        if call_id and (known_call_ids is None or call_id in known_call_ids):
            return {
                "type": "function_call_output",
                "call_id": call_id,
                "output": output,
            }
        label = f"Tool result ({call_id}):" if call_id else "Tool result:"
        return self._input_text_message("user", f"{label}\n{output}")

    def _convert_history(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ark_history = []
        known_call_ids: set[str] = set()
        tool_result_ids = {
            str(item.get("tool_call_id", "")).strip()
            for item in messages
            if isinstance(item, dict)
            and str(item.get("role", "")).strip() == "tool"
            and item.get("tool_call_id")
        }
        for msg in messages:
            if not isinstance(msg, dict):
                continue

            role = str(msg.get("role", "")).strip()
            if role == "system":
                sys_prompt = self._stringify_content(msg.get("content", ""))
                if sys_prompt:
                    ark_history.append(self._input_text_message("system", sys_prompt))
                continue

            if role in ("user", "assistant"):
                content = self._stringify_content(msg.get("content", ""))
                has_tool_calls = isinstance(msg.get("tool_calls"), list) and bool(msg.get("tool_calls"))
                tool_call_items = self._convert_tool_calls(msg, tool_result_ids) if role == "assistant" else []
                known_call_ids.update(item["call_id"] for item in tool_call_items)
                if content or role == "user" or (not tool_call_items and not has_tool_calls):
                    ark_history.append(self._input_text_message(role, content))
                ark_history.extend(tool_call_items)
                continue

            if role == "tool":
                ark_history.append(self._convert_tool_result(msg, known_call_ids))
        return ark_history

    def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float,
        image_paths: List[str] | None = None,
        **kwargs,
    ) -> Generator[Dict[str, Any], None, None]:
        client = Ark(base_url=self.base_url, api_key=self.api_key)

        old_ver = self.model_name in {"doubao-seed-1-6-flash-250828", "deepseek-v3-2-251201"}
        reasoning_effort = kwargs.get("reasoningEffort", "medium")
        enable_search = kwargs.get("enable_search", False)
        keyword_count_mapping = {"minimal": 2, "low": 4, "medium": 8, "high": 12}

        tools = (
            [{"type": "web_search", "max_keyword": keyword_count_mapping.get(reasoning_effort, 1)}]
            if enable_search
            else None
        )
        tool_call_history: list[dict[str, Any]] = []

        req_messages = self._convert_history(messages)
        file_ids: list[str] = []

        if old_ver and reasoning_effort == "minimal":
            thinking_mode = "disabled"
        else:
            thinking_mode = "enabled"

        if image_paths:
            for index, img_path in enumerate(image_paths):
                yield {
                    "type": "system",
                    "content": f"正在上传图片 {index + 1}/{len(image_paths)}: {img_path}...\n",
                }
                file = client.files.create(file=open(img_path, "rb"), purpose="user_data")
                file_id = file.id
                file_ids.append(file_id)
                target_message = next(
                    (
                        message
                        for message in reversed(req_messages)
                        if message.get("role") == "user" and isinstance(message.get("content"), list)
                    ),
                    None,
                )
                if target_message is None:
                    target_message = self._input_text_message("user", "")
                    req_messages.append(target_message)
                target_message["content"].append({"type": "input_image", "file_id": file_id})

        response = (
            client.responses.create(
                model=self.model_name,
                input=req_messages,
                temperature=temperature,
                stream=True,
                thinking={"type": "enabled"},
                tools=tools,
                reasoning={"effort": reasoning_effort},
            )
            if not old_ver
            else client.responses.create(
                model=self.model_name,
                input=req_messages,
                temperature=temperature,
                stream=True,
                thinking={"type": thinking_mode},
                tools=tools,
            )
        )

        begin_time = time.time()
        is_thinking = False
        search_queries: list[str] = []
        search_sources: list[str] = []

        def append_unique(values: list[str], value: str | None) -> None:
            if value and value not in values:
                values.append(value)

        def collect_url_citation(annotation: Any) -> None:
            if not annotation or getattr(annotation, "type", None) != "url_citation":
                return
            url = getattr(annotation, "url", None)
            title = getattr(annotation, "title", None) or url
            if url:
                append_unique(search_sources, f"[{title}]({url})")

        def collect_from_output_item(item: Any) -> None:
            if not item:
                return
            if getattr(item, "type", None) == "web_search_call":
                action = getattr(item, "action", None)
                if action:
                    append_unique(search_queries, getattr(action, "query", None))
            for part in getattr(item, "content", None) or []:
                for annotation in getattr(part, "annotations", None) or []:
                    collect_url_citation(annotation)

        for event in response:
            if isinstance(event, ResponseReasoningSummaryTextDeltaEvent):
                is_thinking = True
                yield {"type": "thinking", "content": event.delta}
                continue

            if isinstance(event, ResponseTextDeltaEvent):
                if is_thinking:
                    yield {"type": "meta", "thinking_time": time.time() - begin_time}
                    is_thinking = False
                yield {"type": "content", "content": event.delta}
                continue

            if not hasattr(event, "type"):
                continue
            if event.type in {"response.output_item.added", "response.output_item.done"}:
                collect_from_output_item(getattr(event, "item", None))
            elif event.type == "response.output_text.annotation.added":
                collect_url_citation(getattr(event, "annotation", None))

        try:
            for file_id in file_ids:
                client.files.delete(file_id=file_id)
        except Exception as exc:
            yield {
                "type": "system",
                "content": f"未能删除上传的文件，可能会占用存储空间。错误详情: {exc}",
            }

        if reasoning_effort == "minimal":
            reasoning_effort = None

        if enable_search and search_queries:
            tool_call_history.append(
                {
                    "name": "web_search",
                    "status": "success" if search_sources else "no_results",
                }
            )

        yield {
            "type": "meta",
            "think_level": reasoning_effort if reasoning_effort is not None else None,
            "uris": search_sources,
            "search_keywords": search_queries,
            "tool_call_history": tool_call_history,
        }

        client.close()
