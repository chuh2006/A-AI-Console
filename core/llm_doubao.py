import time
import pathlib
import json
from typing import Generator, Dict, Any, List
from .llm_base import BaseLLMClient
from volcenginesdkarkruntime import Ark
from volcenginesdkarkruntime.types.responses.response_reasoning_summary_text_delta_event import ResponseReasoningSummaryTextDeltaEvent
from volcenginesdkarkruntime.types.responses.response_text_delta_event import ResponseTextDeltaEvent

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

    def _convert_tool_calls(self, msg: Dict[str, Any], valid_call_ids: set[str] | None = None) -> List[Dict[str, str]]:
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

            converted_tool_calls.append({
                "type": "function_call",
                "call_id": call_id,
                "name": name,
                "arguments": arguments_text,
            })

        return converted_tool_calls

    def _convert_tool_result(self, msg: Dict[str, Any], known_call_ids: set[str] | None = None) -> Dict[str, Any]:
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
        """将 OpenAI 格式历史转换为 Volcengine Ark 格式"""
        ark_history = []
        known_call_ids: set[str] = set()
        tool_result_ids = {
            str(item.get("tool_call_id", "")).strip()
            for item in messages
            if isinstance(item, dict) and str(item.get("role", "")).strip() == "tool" and item.get("tool_call_id")
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

    def chat_stream(self, messages: List[Dict[str, Any]], temperature: float, image_paths: List[str] = None, **kwargs) -> Generator[Dict[str, Any], None, None]:
        client = Ark(base_url=self.base_url, api_key=self.api_key)

        old_ver = False
        reasoning_effort = kwargs.get("reasoningEffort", "medium")
        enable_search = kwargs.get("enable_search", False)
        keyWordsCountMapping = {"minimal": 2, "low": 4, "medium": 8, "high": 12}

        if self.model_name in ["doubao-seed-1-6-flash-250828"]:
            old_ver = True
        tools = [{
            "type": "web_search",
            "max_keyword": keyWordsCountMapping.get(reasoning_effort, 1)
        }] if enable_search else None
        tool_call_history = []  # 用于记录工具调用的历史，包含工具名称和调用状态（成功/被拒绝）

        req_messages = self._convert_history(messages)
        file_ids = []
        if old_ver and reasoning_effort == "minimal":
            enable_search_client = "disabled"  # 旧版本为enable和disable二元状态
        else:
            enable_search_client = "enabled"

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
                target_message = next(
                    (
                        message for message in reversed(req_messages)
                        if message.get("role") == "user" and isinstance(message.get("content"), list)
                    ),
                    None,
                )
                if target_message is None:
                    target_message = self._input_text_message("user", "")
                    req_messages.append(target_message)
                target_message["content"].append({"type": "input_image", "file_id": file_id})

        response = client.responses.create(
            model = self.model_name,
            input=req_messages,
            temperature=temperature,
            stream=True,
            thinking={"type": "enabled"},
            tools=tools,
            reasoning={"effort": reasoning_effort}
        ) if not old_ver else client.responses.create(
            model = self.model_name,
            input=req_messages,
            temperature=temperature,
            stream=True,
            thinking={"type": enable_search_client},
            tools=tools
        )

        begin_time = time.time()
        isThinking = False
        search_queries = []
        search_sources = []

        def _append_unique(values: list[str], value: str | None):
            if value and value not in values:
                values.append(value)

        def _collect_url_citation(annotation: Any):
            if not annotation:
                return
            anno_type = getattr(annotation, "type", None)
            if anno_type != "url_citation":
                return
            url = getattr(annotation, "url", None)
            title = getattr(annotation, "title", None) or url
            if url:
                _append_unique(search_sources, f"[{title}]({url})")

        def _collect_from_output_item(item: Any):
            if not item:
                return

            # Web Search 的查询词在 web_search_call.action.query
            if getattr(item, "type", None) == "web_search_call":
                action = getattr(item, "action", None)
                if action:
                    _append_unique(search_queries, getattr(action, "query", None))

            # 输出文本里的注释会携带 url_citation（标题+链接）
            content = getattr(item, "content", None) or []
            for part in content:
                annotations = getattr(part, "annotations", None) or []
                for annotation in annotations:
                    _collect_url_citation(annotation)

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
            elif hasattr(event, 'type'):
                # 根据 Responses API 事件模型提取搜索关键词与引用链接
                if event.type in ('response.output_item.added', 'response.output_item.done'):
                    _collect_from_output_item(getattr(event, 'item', None))
                elif event.type == 'response.output_text.annotation.added':
                    _collect_url_citation(getattr(event, 'annotation', None))
            else:
                continue

        try:
            for file_id in file_ids:
                client.files.delete(file_id=file_id)
        except Exception as e:
            yield {"type": "system", "content": f"未能删除上传的文件，可能会占用存储空间。错误详情: {e}"}

        if reasoning_effort == "minimal":
            reasoning_effort = None  # 后端不区分 minimal 和 None，前端展示时也不特别标注 minimal，保持简洁
        
        if enable_search and search_queries:
            tool_call_history.append({
                "name": "web_search",
                "status": "success" if search_sources else "no_results"
            })
            
        yield {"type": "meta", "think_level": reasoning_effort if reasoning_effort is not None else None, "uris": search_sources, "search_keywords": search_queries, "tool_call_history": tool_call_history}

        client.close()
