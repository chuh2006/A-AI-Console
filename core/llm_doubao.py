import base64
import json
import mimetypes
import os
import pathlib
import time
import uuid
from typing import Any, Dict, Generator, List

import httpx
from volcenginesdkarkruntime import Ark
from volcenginesdkarkruntime.types.images import ContentGenerationTool, SequentialImageGenerationOptions
from volcenginesdkarkruntime.types.responses.response_reasoning_summary_text_delta_event import ResponseReasoningSummaryTextDeltaEvent
from volcenginesdkarkruntime.types.responses.response_text_delta_event import ResponseTextDeltaEvent

from .llm_base import BaseLLMClient


class VolcengineClient(BaseLLMClient):
    IMAGE_MODELS = {
        "doubao-seedream-5-0-260128",
        "doubao-seedream-4-5-251128",
    }
    IMAGE_SUMMARY_MODEL = "doubao-seed-2-0-lite-260215"
    IMAGE_REF_LIMIT = 14
    IMAGE_TOTAL_LIMIT = 15

    def _create_client(self) -> Ark:
        return Ark(base_url=self.base_url, api_key=self.api_key)

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
                continue # 系统消息不直接加入历史
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

    def _extract_text_from_response_object(self, response: Any) -> str:
        parts: list[str] = []
        output_items = getattr(response, "output", None) or []
        for item in output_items:
            if getattr(item, "type", None) != "message":
                continue
            for content_item in getattr(item, "content", None) or []:
                if getattr(content_item, "type", None) != "output_text":
                    continue
                text = getattr(content_item, "text", None)
                if text:
                    parts.append(str(text))
        return "".join(parts).strip()

    def _extract_latest_user_message(self, messages: List[Dict[str, Any]]) -> tuple[str, int]:
        for index in range(len(messages) - 1, -1, -1):
            message = messages[index]
            if not isinstance(message, dict):
                continue
            if str(message.get("role", "")).strip() != "user":
                continue
            return self._stringify_content(message.get("content", "")).strip(), index
        return "", -1

    def _build_summary_history_text(
        self,
        messages: List[Dict[str, Any]],
        latest_user_index: int,
    ) -> str:
        transcript_parts: list[str] = []
        for idx, message in enumerate(messages):
            if idx == latest_user_index:
                continue
            if not isinstance(message, dict):
                continue
            role = str(message.get("role", "")).strip()
            if role not in {"system", "user", "assistant"}:
                continue
            content = self._stringify_content(message.get("content", "")).strip()
            if not content:
                continue
            if len(content) > 2400:
                content = content[:2400] + "..."
            transcript_parts.append(f"[{role}]\n{content}")

        transcript = "\n\n".join(transcript_parts).strip()
        if len(transcript) > 24000:
            transcript = transcript[-24000:]
        return transcript

    def _summarize_image_context(
        self,
        client: Ark,
        messages: List[Dict[str, Any]],
        latest_user_text: str,
    ) -> tuple[str, float]:
        latest_user_index = -1
        for index in range(len(messages) - 1, -1, -1):
            message = messages[index]
            if isinstance(message, dict) and str(message.get("role", "")).strip() == "user":
                latest_user_index = index
                break

        if latest_user_index <= 0:
            return "", 0.0

        history_text = self._build_summary_history_text(messages, latest_user_index)
        if not history_text:
            return "", 0.0

        summary_prompt = (
            "你要为后续图像生成整理前序上下文。\n"
            "目标是保留继续生成图片所必须的信息，而不是只关注人物或场景。\n\n"

            "请先判断任务属于哪一类：\n"
            "1. 人物/角色图\n"
            "2. 产品介绍图/电商图\n"
            "3. 信息图/表格图/PPT页/知识卡片\n"
            "4. UI界面/宣传图\n"
            "5. 场景概念图\n"
            "6. Logo/IP设计\n\n"

            "按类型提炼：\n\n"

            "【信息图/表格图/PPT页】重点保留：\n"
            "标题、栏目结构、表格列名、对比关系、核心数据、数字、百分比、"
            "加粗强调项、文案内容、信息层级、页面布局、视觉风格。\n"
            "数字和原始文案必须尽量原样保留，不可抽象总结。\n\n"

            "【产品介绍图】重点保留：\n"
            "产品名称、品牌、卖点、参数规格、标题、副标题、卖点文案、版式要求。\n\n"

            "【人物图】重点保留：\n"
            "主体、身份、外貌、服装、姿态、镜头、构图、风格、色彩。\n\n"

            "【UI图】重点保留：\n"
            "页面结构、模块布局、信息层级、品牌风格。\n\n"

            "【场景图】重点保留：\n"
            "场景主体、空间关系、氛围、风格、光线。\n\n"

            "【Logo/IP】重点保留：\n"
            "品牌名、核心意象、设计风格、禁忌元素。\n\n"

            "规则：\n"
            "1. 优先保留具体信息，尤其是数字、文案、表格内容。\n"
            "2. 不要因为没有人物/镜头信息就输出“无”。\n"
            "3. 只要前序内容会影响下一次生图，就必须保留。\n"
            "4. 不要解释，不要寒暄，不要编造。\n"
            "5. 若确实完全无关，再输出“无”。\n"
            "6. 生图模型只能看到你的总结，必须确保信息详细完整。\n\n"

            f"当前用户新消息：\n{latest_user_text}\n\n"
            f"前序对话：\n{history_text}"
        )

        begin_time = time.time()
        response = client.responses.create(
            model=self.IMAGE_SUMMARY_MODEL,
            input=[self._input_text_message("user", summary_prompt)],
            temperature=0.5,
        )
        summary_text = self._extract_text_from_response_object(response)
        if summary_text == "无":
            summary_text = ""
        return summary_text.strip(), time.time() - begin_time

    def _build_image_prompt(
        self,
        latest_user_text: str,
        summary_text: str,
        reference_count: int,
        requested_count: int,
    ) -> str:
        latest_text = str(latest_user_text or "").strip()
        summary = str(summary_text or "").strip()
        image_count = max(1, int(requested_count or 1))
        reference_prompt = (
            f"请基于提供的参考图继续生成 {image_count} 张图片。"
            if reference_count > 0
            else f"请生成 {image_count} 张图片。"
        )

        if not summary:
            return latest_text or reference_prompt

        if not latest_text:
            return (
                f"前序对话摘要：\n{summary}\n\n"
                f"本轮输入包含 {reference_count} 张参考图。\n"
                f"{reference_prompt}"
            ).strip()

        return (
            f"前序对话摘要：\n{summary}\n\n"
            f"本轮用户新需求：\n{latest_text}"
            "\n请生成图片。"
        ).strip()

    def _project_root(self) -> pathlib.Path:
        return pathlib.Path(__file__).resolve().parent.parent

    def _get_generated_image_dir(self) -> pathlib.Path:
        image_dir = self._project_root() / "chat_result" / "generate" / time.strftime("%Y-%m-%d")
        image_dir.mkdir(parents=True, exist_ok=True)
        return image_dir

    def _generate_unique_image_name(self, extension: str) -> str:
        ext = (extension or ".png").lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        return f"generate_{uuid.uuid4().hex}{ext}"

    def _local_image_to_data_url(self, path: str) -> str:
        mime_type, _ = mimetypes.guess_type(path)
        mime_type = mime_type or "image/png"
        with open(path, "rb") as handle:
            encoded = base64.b64encode(handle.read()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    def _normalize_image_size(self, raw_size: Any) -> str:
        value = str(raw_size or "").strip()
        if not value:
            return "2K"

        upper_value = value.upper()
        preset_map = {
            "1K": "1K",
            "2K": "2K",
            "3K": "3K",
            "4K": "4K",
        }
        if upper_value in preset_map:
            return preset_map[upper_value]

        normalized = value.lower().replace("×", "x").replace("脳", "x").replace("*", "x")
        normalized = normalized.replace(" ", "")
        if normalized.count("x") == 1:
            left, right = normalized.split("x", 1)
            if left.isdigit() and right.isdigit():
                return f"{int(left)}x{int(right)}"

        return "2K"

    def _resolve_placeholder_count(self, image_paths: List[str], kwargs: Dict[str, Any]) -> int:
        try:
            requested = int(kwargs.get("requested_image_count", 1))
        except (TypeError, ValueError):
            requested = 1

        remaining_budget = self.IMAGE_TOTAL_LIMIT - len(image_paths)
        if remaining_budget <= 0:
            return 0
        return max(1, min(requested, remaining_budget))

    def _download_image_asset(self, url: str) -> tuple[bytes, str]:
        response = httpx.get(url, timeout=120.0, follow_redirects=True)
        response.raise_for_status()
        return response.content, response.headers.get("content-type", "")

    def _save_generated_image(
        self,
        *,
        image_index: int,
        url: str,
        b64_json: str,
        requested_output_format: str,
    ) -> str:
        image_dir = self._get_generated_image_dir()
        mime_type = ""
        binary = b""

        if url:
            binary, mime_type = self._download_image_asset(url)
        elif b64_json:
            binary = base64.b64decode(b64_json)

        if not binary:
            raise ValueError(f"第 {image_index + 1} 张图片没有返回可保存的数据。")

        extension = ""
        if requested_output_format in {"png", "jpeg", "jpg", "webp"}:
            extension = ".jpg" if requested_output_format == "jpg" else f".{requested_output_format}"
        elif mime_type:
            guessed = mimetypes.guess_extension(mime_type.split(";", 1)[0].strip())
            extension = guessed or ""
        if not extension:
            extension = ".jpeg"

        target_path = image_dir / self._generate_unique_image_name(extension)
        with open(target_path, "wb") as handle:
            handle.write(binary)
        return str(target_path)

    def _stream_image_generation(
        self,
        client: Ark,
        messages: List[Dict[str, Any]],
        temperature: float,
        image_paths: List[str] | None = None,
        **kwargs,
    ) -> Generator[Dict[str, Any], None, None]:
        del temperature
        image_paths = list(image_paths or [])
        latest_user_text, _ = self._extract_latest_user_message(messages)
        if not latest_user_text and not image_paths:
            raise ValueError("图片生成请求缺少文本提示词或参考图。")

        if len(image_paths) > self.IMAGE_REF_LIMIT:
            yield {
                "type": "system",
                "content": f"参考图最多支持 {self.IMAGE_REF_LIMIT} 张，已自动截取前 {self.IMAGE_REF_LIMIT} 张继续生成。\n",
            }
            image_paths = image_paths[: self.IMAGE_REF_LIMIT]

        remaining_budget = self.IMAGE_TOTAL_LIMIT - len(image_paths)
        if remaining_budget <= 0:
            raise ValueError("当前参考图数量已达到上限，无法继续生成新图片。")

        enable_image_thinking = bool(kwargs.get("enable_image_thinking", True))
        summary_text = ""
        summary_elapsed = 0.0
        try:
            summary_text, summary_elapsed = self._summarize_image_context(client, messages, latest_user_text)
        except Exception as exc:
            yield {
                "type": "system",
                "content": f"前序上下文概括失败，已退回为仅使用当前输入继续生图。错误详情: {exc}\n",
            }
            summary_text = ""
            summary_elapsed = 0.0

        if enable_image_thinking and summary_text:
            yield {
                "type": "thinking",
                "content": f"前序对话概括：{summary_text}",
            }
            if summary_elapsed > 0:
                yield {"type": "meta", "thinking_time": summary_elapsed}

        requested_size = self._normalize_image_size(kwargs.get("resolution", "2K"))
        requested_output_format = str(kwargs.get("output_format", "jpeg") or "jpeg").strip().lower()
        if requested_output_format not in {"jpeg", "png", "webp"}:
            requested_output_format = "jpeg"

        placeholder_count = self._resolve_placeholder_count(image_paths, kwargs)
        image_prompt = self._build_image_prompt(
            latest_user_text=latest_user_text,
            summary_text=summary_text,
            reference_count=len(image_paths),
            requested_count=placeholder_count,
        )
        yield {
            "type": "image_placeholder",
            "count": placeholder_count,
        }

        tools = None
        if kwargs.get("enable_search"):
            tools = [ContentGenerationTool(type="web_search")]

        seq_mode = str(kwargs.get("sequential_image_generation", "disabled")).strip().lower()
        seq_options = None
        if seq_mode == "auto":
            raw_options = kwargs.get("sequential_image_generation_options", {})
            if not isinstance(raw_options, dict):
                raw_options = {}
            try:
                requested_max_images = int(raw_options.get("max_images", placeholder_count))
            except (TypeError, ValueError):
                requested_max_images = placeholder_count
            requested_max_images = max(
                1,
                min(requested_max_images, self.IMAGE_TOTAL_LIMIT - len(image_paths)),
            )
            seq_options = SequentialImageGenerationOptions(max_images=requested_max_images)

        image_payload: str | list[str] | None = None
        if image_paths:
            encoded_images = [self._local_image_to_data_url(path) for path in image_paths]
            image_payload = encoded_images[0] if len(encoded_images) == 1 else encoded_images

        request_kwargs: dict[str, Any] = {
            "model": self.model_name,
            "prompt": image_prompt,
            "image": image_payload,
            "response_format": "url",
            "size": requested_size,
            "watermark": False,
            "stream": True,
        }
        if tools:
            request_kwargs["tools"] = tools
        if self.model_name == "doubao-seedream-5-0-260128":
            request_kwargs["output_format"] = requested_output_format
        if seq_mode == "auto" and seq_options is not None:
            request_kwargs["sequential_image_generation"] = "auto"
            request_kwargs["sequential_image_generation_options"] = seq_options

        generated_paths: list[str] = []
        failed_images: list[dict[str, Any]] = []
        response_error_message = ""
        usage = None
        completed_indices: set[int] = set()
        with client.images.generate(**request_kwargs) as response:
            for event in response:
                event_type = str(getattr(event, "type", "") or "").strip().lower()
                event_error = getattr(event, "error", None)
                event_error_message = str(getattr(event_error, "message", "") or "").strip()
                if not hasattr(event, "image_index"):
                    if event_type.endswith("completed"):
                        usage = getattr(event, "usage", None)
                        response_error_message = event_error_message or response_error_message
                    continue
                try:
                    item_index = int(getattr(event, "image_index", len(completed_indices)) or 0)
                except (TypeError, ValueError):
                    item_index = len(completed_indices)
                if item_index in completed_indices:
                    continue
                item_url = str(getattr(event, "url", "") or "").strip()
                item_b64 = str(getattr(event, "b64_json", "") or "").strip()
                item_size = str(getattr(event, "size", "") or requested_size)
                if event_error_message and not item_url and not item_b64:
                    completed_indices.add(item_index)
                    failed_images.append({"index": item_index, "error": event_error_message})
                    yield {
                        "type": "image_failed",
                        "index": item_index,
                        "error": event_error_message,
                    }
                    continue
                if not item_url and not item_b64:
                    continue
                try:
                    saved_path = self._save_generated_image(
                        image_index=item_index,
                        url=item_url,
                        b64_json=item_b64,
                        requested_output_format=requested_output_format,
                    )
                except Exception as exc:
                    completed_indices.add(item_index)
                    failed_images.append({"index": item_index, "error": str(exc)})
                    yield {
                        "type": "image_failed",
                        "index": item_index,
                        "error": str(exc),
                    }
                    continue

                completed_indices.add(item_index)
                generated_paths.append(saved_path)
                yield {
                    "type": "image_generated",
                    "index": item_index,
                    "image_path": saved_path,
                    "size": item_size,
                    "source_url": item_url,
                }

        if not generated_paths:
            error_message = response_error_message or "模型没有返回可用图片。"
            if failed_images:
                error_message = f"{error_message} 已有 {len(failed_images)} 张图片保存失败。"
            raise ValueError(error_message)

        tool_call_history: list[dict[str, Any]] = []
        if tools:
            tool_usage = getattr(usage, "tool_usage", None)
            web_search_count = int(getattr(tool_usage, "web_search", 0) or 0)
            tool_call_history.append(
                {
                    "name": "web_search",
                    "status": "success" if web_search_count > 0 else "enabled",
                    "count": web_search_count,
                }
            )

        yield {
            "type": "meta",
            "generated_images": generated_paths,
            "tool_call_history": tool_call_history,
            "image_failures": failed_images,
        }

    def _stream_text_chat(
        self,
        client: Ark,
        messages: List[Dict[str, Any]],
        temperature: float,
        image_paths: List[str] | None = None,
        **kwargs,
    ) -> Generator[Dict[str, Any], None, None]:
        old_ver = self.model_name in {"doubao-seed-1-6-flash-250828", "deepseek-v3-2-251201"}
        reasoning_effort = kwargs.get("reasoningEffort", "medium")
        enable_search = kwargs.get("enable_search", False)
        keyword_count_mapping = {"minimal": 2, "low": 4, "medium": 8, "high": 12}

        tools = None
        if enable_search:
            tools = [{"type": "web_search", "max_keyword": keyword_count_mapping.get(reasoning_effort, 1)}]

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

        tool_call_history: list[dict[str, Any]] = []
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

    def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float,
        image_paths: List[str] | None = None,
        **kwargs,
    ) -> Generator[Dict[str, Any], None, None]:
        client = self._create_client()
        try:
            if self.model_name in self.IMAGE_MODELS:
                yield from self._stream_image_generation(
                    client,
                    messages=messages,
                    temperature=temperature,
                    image_paths=image_paths,
                    **kwargs,
                )
            else:
                yield from self._stream_text_chat(
                    client,
                    messages=messages,
                    temperature=temperature,
                    image_paths=image_paths,
                    **kwargs,
                )
        finally:
            client.close()
