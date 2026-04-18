from anthropic import Anthropic
from typing import Any, Dict, Generator, List, Tuple
import time
from .llm_base import BaseLLMClient
from tools.vision_tools import perform_ocr
from tools.web_search_ds import web_search_tool_schema, search_web


class AnthropicLLMClient(BaseLLMClient):
    def _convert_history(self, messages: List[Dict[str, str | list]]) -> Tuple[str | None, List[Dict[str, Any]]]:
        system_parts: List[str] = []
        converted: List[Dict[str, Any]] = []

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
                else:
                    converted.append({"role": "assistant", "content": str(content)})

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

        if self.model_name == "MiniMax-M2.5" and "马嘉祺" in req_messages[-1]["content"][0].get("text", ""):
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

        def _extend_unique(target: List[str], values: List[Any]) -> None:
            for value in values:
                if not isinstance(value, str):
                    continue
                normalized = value.strip()
                if normalized and normalized not in target:
                    target.append(normalized)

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

                req_messages.append({
                    "role": "assistant",
                    "content": [self._dump_content_block(block) for block in final_message.content],
                })

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

            final_meta: Dict[str, Any] = {}
            if search_keywords:
                final_meta["search_keywords"] = search_keywords
            if search_sources:
                final_meta["uris"] = search_sources
            if tool_call_history:
                final_meta["tool_call_history"] = tool_call_history
            if final_meta:
                yield {"type": "meta", **final_meta}
        finally:
            client.close()
