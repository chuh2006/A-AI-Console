from anthropic import Anthropic
from typing import Any, Dict, Generator, List, Tuple
import json
import time
from .llm_base import BaseLLMClient
from tools.vision_tools import perform_ocr
from tools.web_search_ds import web_search_tool_schema, search_web


class AnthropicLLMClient(BaseLLMClient):
    def _extract_tool_use_ids(self, content_blocks: Any) -> set[str]:
        tool_use_ids: set[str] = set()
        if not isinstance(content_blocks, list):
            return tool_use_ids

        for block in content_blocks:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "tool_use":
                continue
            tool_use_id = str(block.get("id", "")).strip()
            if tool_use_id:
                tool_use_ids.add(tool_use_id)
        return tool_use_ids

    def _convert_openai_tool_calls(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        tool_uses: List[Dict[str, Any]] = []
        raw_tool_calls = message.get("tool_calls", [])
        if not isinstance(raw_tool_calls, list):
            return tool_uses

        for tool_call in raw_tool_calls:
            if not isinstance(tool_call, dict):
                continue

            tool_use_id = str(tool_call.get("id", "")).strip()
            function_info = tool_call.get("function", {})
            if not isinstance(function_info, dict):
                function_info = {}
            tool_name = str(function_info.get("name", "")).strip()
            raw_arguments = function_info.get("arguments", {})

            if not tool_use_id or not tool_name:
                continue

            tool_input: Dict[str, Any] = {}
            if isinstance(raw_arguments, dict):
                tool_input = raw_arguments
            elif isinstance(raw_arguments, str):
                arg_text = raw_arguments.strip()
                if arg_text:
                    try:
                        decoded = json.loads(arg_text)
                        if isinstance(decoded, dict):
                            tool_input = decoded
                    except json.JSONDecodeError:
                        tool_input = {}

            tool_uses.append({
                "type": "tool_use",
                "id": tool_use_id,
                "name": tool_name,
                "input": tool_input,
            })

        return tool_uses

    def _convert_history(self, messages: List[Dict[str, str | list]]) -> Tuple[str | None, List[Dict[str, Any]]]:
        system_parts: List[str] = []
        converted: List[Dict[str, Any]] = []
        pending_tool_use_ids: set[str] = set()

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                if content:
                    system_parts.append(str(content))
                continue

            if role == "user":
                if isinstance(content, list):
                    converted.append({"role": "user", "content": content})
                else:
                    converted.append({"role": "user", "content": [{"type": "text", "text": str(content)}]})
            elif role == "assistant":
                if isinstance(content, list):
                    converted.append({"role": "assistant", "content": content})
                    pending_tool_use_ids.update(self._extract_tool_use_ids(content))
                elif isinstance(msg.get("tool_calls"), list):
                    assistant_blocks: List[Dict[str, Any]] = []
                    if content:
                        assistant_blocks.append({"type": "text", "text": str(content)})
                    tool_uses = self._convert_openai_tool_calls(msg)
                    assistant_blocks.extend(tool_uses)
                    if assistant_blocks:
                        converted.append({"role": "assistant", "content": assistant_blocks})
                        pending_tool_use_ids.update(self._extract_tool_use_ids(assistant_blocks))
                    else:
                        converted.append({"role": "assistant", "content": str(content)})
                else:
                    converted.append({"role": "assistant", "content": str(content)})
            elif role == "tool":
                tool_call_id = str(msg.get("tool_call_id", "")).strip()
                if not tool_call_id or tool_call_id not in pending_tool_use_ids:
                    # 历史中若缺少对应的 assistant/tool_use，则该 tool_result 会触发 400，需跳过。
                    continue

                pending_tool_use_ids.remove(tool_call_id)
                tool_result = {
                    "type": "tool_result",
                    "tool_use_id": tool_call_id,
                    "content": content,
                }
                previous_content = converted[-1].get("content") if converted and converted[-1].get("role") == "user" else None
                if (
                    isinstance(previous_content, list)
                    and previous_content
                    and all(isinstance(block, dict) and block.get("type") == "tool_result" for block in previous_content)
                ):
                    previous_content.append(tool_result)
                else:
                    converted.append({"role": "user", "content": [tool_result]})

        system_prompt = "\n\n".join(part for part in system_parts if part).strip()
        return system_prompt or None, converted

    def _convert_tool_schema(self, tool_schema: Dict[str, Any]) -> Dict[str, Any]:
        function_schema = tool_schema.get("function", {})
        return {
            "name": function_schema.get("name", ""),
            "description": function_schema.get("description", ""),
            "input_schema": function_schema.get("parameters", {"type": "object", "properties": {}}),
        }

    def _dump_content_block(self, block: Any) -> Dict[str, Any]:
        if hasattr(block, "model_dump"):
            return block.model_dump(exclude_none=True)
        return dict(block)

    def _append_ocr_to_last_user_message(self, req_messages: List[Dict[str, Any]], image_paths: List[str]) -> None:
        if not image_paths:
            return

        for msg in reversed(req_messages):
            if msg.get("role") != "user":
                continue

            content_blocks = msg.setdefault("content", [])
            text_block = next((block for block in content_blocks if block.get("type") == "text"), None)
            if text_block is None:
                text_block = {"type": "text", "text": ""}
                content_blocks.insert(0, text_block)

            for img_path in image_paths:
                ocr_result = perform_ocr(img_path)
                text_block["text"] += f"\n\nsystem:\n【附加图片OCR内容】\n{ocr_result}"
            break

    def chat_stream(
        self,
        messages: List[Dict[str, str | list]],
        temperature: float,
        image_paths: List[str] = None,
        **kwargs
    ) -> Generator[Dict[str, Any], None, None]:
        
        system_prompt, req_messages = self._convert_history(messages)
        using_minimax = "minimax" in self.model_name.lower()
        special = False

        last_text = ""
        if req_messages:
            last_content = req_messages[-1].get("content", "")
            if isinstance(last_content, list):
                for block in last_content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        last_text = str(block.get("text", ""))
                        break
            else:
                last_text = str(last_content)

        if self.model_name == "MiniMax-M2.5" and "马嘉祺" in last_text:
            special = True

        if using_minimax and temperature >= 1.0:
            temperature = 1.0
        if using_minimax:
            self._append_ocr_to_last_user_message(req_messages, image_paths or [])

        tools = []
        if kwargs.get("enable_search", False):
            tools.append(self._convert_tool_schema(web_search_tool_schema))

        max_iterations = 5 if tools else 0
        loop_count = 0
        tool_call_history: List[Dict[str, str]] = []
        search_keywords: List[str] = []
        search_sources: List[str] = []
        req_tool_calls: List[Dict] = []  # 记录发送给模型的工具调用信息，包含工具名称、调用参数等
        history_messages: List[Dict[str, Any]] = []  # 记录本轮 assistant/tool 的真实顺序消息

        def _extend_unique(target: List[str], values: List[Any]) -> None:
            for value in values:
                if not isinstance(value, str):
                    continue
                normalized = value.strip()
                if normalized and normalized not in target:
                    target.append(normalized)

        def _append_history_message(message: Dict[str, Any]) -> None:
            if not isinstance(message, dict):
                return
            history_messages.append(dict(message))

        def _build_assistant_tool_call_message(content_blocks: List[Any]) -> Dict[str, Any]:
            text_parts: List[str] = []
            tool_calls: List[Dict[str, Any]] = []
            for block in content_blocks:
                dumped = self._dump_content_block(block)
                block_type = str(dumped.get("type", "")).strip()
                if block_type == "text":
                    text_parts.append(str(dumped.get("text", "")))
                    continue
                if block_type != "tool_use":
                    continue

                tool_input = dumped.get("input", {})
                if not isinstance(tool_input, dict):
                    tool_input = {}
                tool_calls.append({
                    "id": str(dumped.get("id", "")).strip(),
                    "type": "function",
                    "function": {
                        "name": str(dumped.get("name", "")).strip(),
                        "arguments": json.dumps(tool_input, ensure_ascii=False),
                    },
                })

            return {
                "role": "assistant",
                "content": "".join(text_parts),
                "tool_calls": [item for item in tool_calls if item.get("id") and item["function"].get("name")],
            }

        client = Anthropic(api_key=self.api_key, base_url=self.base_url)
        max_tokens = 8192
        if special:
            max_tokens = 2048 # minimax2.5的bug，无法输出字符串“马嘉祺”，所以限制输出长度，避免模型死循环浪费太多token

        try:
            while True:
                loop_count += 1
                begin_time = time.time()
                is_thinking = False
                thinking_time_emitted = False

                request_kwargs: Dict[str, Any] = {
                    "model": self.model_name,
                    "max_tokens": max_tokens,
                    "messages": req_messages,
                    "temperature": temperature,
                    "thinking": {"type": "enabled"},
                }
                if system_prompt:
                    request_kwargs["system"] = system_prompt
                if tools:
                    request_kwargs["tools"] = tools

                with client.messages.stream(**request_kwargs) as stream:
                    for chunk in stream:
                        if chunk.type != "content_block_delta":
                            continue

                        if not hasattr(chunk, "delta") or not chunk.delta:
                            continue

                        if chunk.delta.type == "thinking_delta":
                            is_thinking = True
                            new_thinking = chunk.delta.thinking
                            if new_thinking:
                                yield {"type": "thinking", "content": new_thinking}

                        elif chunk.delta.type == "text_delta":
                            new_text = chunk.delta.text
                            if is_thinking and not thinking_time_emitted:
                                thinking_time_emitted = True
                                is_thinking = False
                                yield {"type": "meta", "thinking_time": time.time() - begin_time}
                            if new_text:
                                yield {"type": "content", "content": new_text}

                    final_message = stream.get_final_message()

                if is_thinking and not thinking_time_emitted:
                    yield {"type": "meta", "thinking_time": time.time() - begin_time}

                tool_uses = [block for block in final_message.content if getattr(block, "type", "") == "tool_use"]
                if not tool_uses:
                    break

                assistant_tool_call_message = _build_assistant_tool_call_message(final_message.content)
                req_messages.append({
                    "role": "assistant",
                    "content": [self._dump_content_block(block) for block in final_message.content],
                })
                if assistant_tool_call_message.get("tool_calls"):
                    _append_history_message(assistant_tool_call_message)

                tool_result_blocks = []
                for tool_use in tool_uses:
                    if loop_count > max_iterations:
                        tool_call_history.append({
                            "name": tool_use.name,
                            "status": "rejected_max_count",
                        })
                        tool_result_blocks.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": "Error: 已达到最大工具调用次数限制，系统强制拦截所有工具调用。请停止尝试调用任何工具",
                            "is_error": True,
                        })
                        continue

                    if tool_use.name == "search_web":
                        raw_queries = tool_use.input.get("queries", []) if isinstance(tool_use.input, dict) else []
                        queries = [q for q in raw_queries if isinstance(q, str) and q.strip()]

                        if queries:
                            yield {"type": "system", "content": f"\033[94m[第{loop_count}轮 | 请求工具] 正在执行网络搜索，关键词: {queries}...\033[0m\n"}
                            search_results = search_web(queries)
                            _extend_unique(search_keywords, queries)
                            _extend_unique(search_sources, search_results.get("sources", []))
                            yield {
                                "type": "system",
                                "content": f"\033[93m[网络搜索返回结果]: {search_results.get('results', '')[:50]}...\033[0m\n",
                            }
                            tool_call_history.append({
                                "name": tool_use.name,
                                "status": "success",
                            })
                            tool_result_blocks.append({
                                "type": "tool_result",
                                "tool_use_id": tool_use.id,
                                "content": search_results.get("results", ""),
                            })
                            req_tool_calls.append({
                                "role": "tool",
                                "tool_call_id": tool_use.id,
                                "content": search_results.get("results", ""),
                            })
                        else:
                            tool_call_history.append({
                                "name": tool_use.name,
                                "status": "invalid_arguments",
                            })
                            tool_result_blocks.append({
                                "type": "tool_result",
                                "tool_use_id": tool_use.id,
                                "content": "Error: search_web 缺少有效的 queries 参数。",
                                "is_error": True,
                            })
                    else:
                        tool_call_history.append({
                            "name": tool_use.name,
                            "status": "not_found",
                        })
                        tool_result_blocks.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": f"Error: Tool '{tool_use.name}' 不存在。请勿再次调用该工具",
                            "is_error": True,
                        })

                req_messages.append({
                    "role": "user",
                    "content": tool_result_blocks,
                })
                for tool_result in tool_result_blocks:
                    if not isinstance(tool_result, dict):
                        continue
                    _append_history_message({
                        "role": "tool",
                        "tool_call_id": tool_result.get("tool_use_id", ""),
                        "content": tool_result.get("content", ""),
                    })

            final_meta: Dict[str, Any] = {}
            if search_keywords:
                final_meta["search_keywords"] = search_keywords
            if search_sources:
                final_meta["uris"] = search_sources
            if tool_call_history:
                final_meta["tool_call_history"] = tool_call_history
            if req_tool_calls:
                final_meta["tool_calls"] = req_tool_calls
            if history_messages:
                final_meta["history_messages"] = history_messages
            if final_meta:
                yield {"type": "meta", **final_meta}
        finally:
            client.close()
