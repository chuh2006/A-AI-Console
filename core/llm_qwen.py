import os
import pathlib
import json
from dashscope import MultiModalConversation
import dashscope 
import time
from .llm_base import BaseLLMClient
from typing import Any, Dict, Generator, List

class QwenClient(BaseLLMClient):
    def _stringify_content(self, content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        try:
            return json.dumps(content, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(content)

    def _format_tool_calls(self, message: Dict[str, Any]) -> str:
        raw_tool_calls = message.get("tool_calls", [])
        if not isinstance(raw_tool_calls, list):
            return ""

        summaries: list[str] = []
        for tool_call in raw_tool_calls:
            if not isinstance(tool_call, dict):
                continue
            function_info = tool_call.get("function", {})
            if not isinstance(function_info, dict):
                function_info = {}
            name = str(function_info.get("name") or tool_call.get("name") or "").strip()
            arguments = self._stringify_content(function_info.get("arguments", ""))
            call_id = str(tool_call.get("id", "") or "").strip()
            if not name and not call_id:
                continue
            label = name or "tool"
            suffix = f" id={call_id}" if call_id else ""
            summaries.append(f"[Tool call: {label}{suffix} arguments={arguments}]")
        return "\n".join(summaries)

    def _format_tool_result(self, message: Dict[str, Any]) -> str:
        call_id = str(message.get("tool_call_id", "") or "").strip()
        label = f"[Tool result id={call_id}]" if call_id else "[Tool result]"
        return f"{label}\n{self._stringify_content(message.get('content', ''))}"

    def _convert_history(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        converted: list[dict[str, Any]] = []
        for msg in messages:
            if not isinstance(msg, dict):
                continue

            role = str(msg.get("role", "")).strip()
            content = msg.get("content", "")

            if role in {"system", "user"}:
                converted.append({"role": role, "content": content if isinstance(content, list) else self._stringify_content(content)})
                continue

            if role == "assistant":
                text = self._stringify_content(content)
                tool_summary = self._format_tool_calls(msg)
                if tool_summary:
                    text = f"{text}\n\n{tool_summary}".strip()
                if text:
                    converted.append({"role": "assistant", "content": text})
                continue

            if role == "tool":
                converted.append({"role": "user", "content": self._format_tool_result(msg)})

        return converted

    def chat_stream(self, messages: List[Dict[str, str | list]], temperature: float, image_paths: List[str] = None, **kwargs) -> Generator[Dict[str, str], None, None]:
        def _safe_get(obj, key, default=None):
            if obj is None:
                return default
            if isinstance(obj, dict):
                return obj.get(key, default)
            try:
                return getattr(obj, key)
            except (AttributeError, KeyError, TypeError):
                return default
        tool_call_history = []  # 用于记录工具调用的历史，包含工具名称和调用状态（成功/被拒绝）
        req_messages = self._convert_history(messages)
        if image_paths:
            last_content = req_messages[-1]["content"]
            new_content = [{"text": self._stringify_content(last_content)}]
            for img_path in image_paths:
                path_url = pathlib.Path(img_path).resolve().as_uri()
                # DashScope expects Windows drive-letter file URIs as file://C:/...
                if os.name == "nt" and path_url.startswith("file:///") and len(path_url) > 10 and path_url[8].isalpha() and path_url[9] == ":":
                    path_url = "file://" + path_url[8:]
                new_content.append({"image": path_url})
            req_messages[-1]["content"] = new_content

        thinking_state = kwargs.get("isQwenThinking", "auto")
        enable_thinking = True if thinking_state == "enabled" else False if thinking_state == "disabled" else None
        enable_search = kwargs.get("enable_search", False)
        search_strategy = kwargs.get("search_strategy", None)

        responses = MultiModalConversation.call(
            api_key=self.api_key,
            model=self.model_name,
            messages=req_messages,
            temperature=temperature,
            stream=True,
            enable_thinking=enable_thinking,
            thinking_budget=10240,
            incremental_output=True,
            enable_search=enable_search,
            search_strategy=search_strategy,
        )
        
        is_thinking = False
        begin_time = time.time()
        search_info = None

        for response in responses:
            output = _safe_get(response, 'output', None)
            if not output:
                continue

            search_info = _safe_get(output, 'search_info', None) if search_info is None else search_info
            choices = _safe_get(output, 'choices', [])
            if choices:
                message = _safe_get(choices[0], 'message', None)
                if message:
                    reasoning_content = _safe_get(message, 'reasoning_content', None)
                    if reasoning_content:
                        is_thinking = True
                        yield {"type": "thinking", "content": reasoning_content}
                    raw_content = _safe_get(message, 'content', None)
                    text_content = ""
                    if isinstance(raw_content, list):
                        for item in raw_content:
                            text_content += _safe_get(item, 'text', '')
                    elif isinstance(raw_content, str):
                        text_content = raw_content
                    if text_content:
                        if is_thinking:
                            think_time = time.time() - begin_time
                            yield {"type": "meta", "thinking_time": think_time}
                            is_thinking = False
                        yield {"type": "content", "content": text_content}

        search_results = []
        if search_info:
            for web in search_info["search_results"]:
                search_results.append(f"[{web['title']}]({web['url']})")

        tool_call_history.append({
            "name": "web_search",
            "status": "success" if search_results else "no_results"
        }) if enable_search else None

        yield {"type": "meta", "uris": search_results, "tool_call_history": tool_call_history}
