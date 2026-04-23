import json
import os
import re
from datetime import datetime

import tools.auto_asker as auto_asker
import tools.prompts as prompts
from tools.chat_archive_renderer import render_chat_archive_html


class ChatSession:
    _TURN_LEADING_ROLES = {"enabled_tools", "image_uploaded", "user_original"}
    _HISTORY_ROLES = {"system", "user", "assistant", "tool"}

    def __init__(self, system_prompt: str = "", first_time: bool = True, enable_system_prompt: bool = True):
        self.history = []
        self.full_context = []
        self.full_context.append({"role": "directions", "content": prompts.Prompts.directions})
        if system_prompt and enable_system_prompt:
            self.history.append({"role": "system", "content": system_prompt})
            self.full_context.append({"role": "system", "content": system_prompt})

    def edit_system_prompt(self, new_prompt: str):
        for msg in self.history:
            if msg["role"] == "system":
                msg["content"] = new_prompt
                break
        else:
            self.history.insert(0, {"role": "system", "content": new_prompt})

        for msg in self.full_context:
            if msg["role"] == "system":
                msg["content"] = new_prompt
                break
        else:
            self.full_context.insert(0, {"role": "system", "content": new_prompt})

    def get_asker_context(self) -> list[dict]:
        context = []
        role_map = {"user": "assistant", "assistant": "user"}
        for msg in self.history:
            if msg["role"] in ["user", "assistant"]:
                context.append({"role": role_map[msg["role"]], "content": msg["content"]})
        return context

    def get_question(self, api_key: str) -> str:
        asker_context = self.get_asker_context()
        if not asker_context:
            return ""
        return auto_asker.get_question(api_key, asker_context)

    def add_epoch_count(self, epoch: int):
        self.full_context.append({"role": "epoch_count", "content": str(epoch)})

    def add_user_message(self, content: str, original_text: str = None, images: list = None):
        if images:
            self.full_context.append({"role": "image_uploaded", "content": list(images)})
        if original_text and original_text != content:
            self.full_context.append({"role": "user_original", "content": original_text})

        self.history.append({"role": "user", "content": content})
        self.full_context.append({"role": "user", "content": content})
        self._auto_clean_context()

    def add_enabled_tools(self, tools: list[str]):
        if tools:
            self.full_context.append({"role": "enabled_tools", "content": list(tools)})

    def add_assistant_message(
        self,
        content: str,
        original_content: str = None,
        thinking: str = "",
        model_name: str = "",
        meta: dict = None,
        ordered_blocks: list[dict] | None = None,
        history_messages: list[dict] | None = None,
    ):
        if ordered_blocks is not None:
            self._append_ordered_assistant_message(
                model_name=model_name,
                ordered_blocks=ordered_blocks,
                history_messages=history_messages or [],
            )
            self._auto_clean_context()
            return

        tool_messages = []
        if meta and meta.get("history_messages"):
            for history_message in meta["history_messages"]:
                if not isinstance(history_message, dict):
                    continue
                role = str(history_message.get("role", "")).strip()
                if role == "assistant" and history_message.get("tool_calls"):
                    assistant_record = dict(history_message)
                    self.history.append(dict(history_message))
                    assistant_record["role"] = "assistant_tool_calls"
                    tool_messages.append(assistant_record)
                elif role == "tool":
                    tool_record = dict(history_message)
                    tool_messages.append(tool_record)
                    self.history.append(dict(tool_record))
        elif meta and meta.get("tool_calls"):
            for tool_call in meta["tool_calls"]:
                if not isinstance(tool_call, dict):
                    continue
                tool_record = dict(tool_call)
                tool_messages.append(tool_record)
                self.history.append(dict(tool_record))
        self.history.append({"role": "assistant", "content": content})

        if model_name:
            self.full_context.append({"role": "model", "content": model_name})

        if tool_messages:
            for tool_message in tool_messages:
                self.full_context.append(dict(tool_message))

        if meta:
            if meta.get("uris"):
                self.full_context.append({"role": "search_results_links", "content": list(meta.get("uris"))})
            if meta.get("think_level"):
                self.full_context.append({"role": "thinking_level", "content": meta.get("think_level")})
            if meta.get("ocr_results"):
                for ocr_item in meta["ocr_results"]:
                    self.full_context.append({
                        "role": "tool_ocr_extraction",
                        "content": {
                            "image_path": ocr_item.get("image_path", ""),
                            "ocr_text": ocr_item.get("ocr_text", ""),
                        },
                    })
            if meta.get("search_keywords"):
                self.full_context.append({"role": "search_keywords", "content": list(meta.get("search_keywords"))})
            if meta.get("assistant_questions"):
                self.full_context.append({"role": "assistant_questions", "content": list(meta.get("assistant_questions"))})
            if meta.get("user_inputs"):
                self.full_context.append({"role": "user_inputs", "content": list(meta.get("user_inputs"))})
            if meta.get("tool_call_history"):
                self.full_context.append({"role": "tool_call_history", "content": list(meta.get("tool_call_history"))})
            if meta.get("meta_title") and meta.get("meta_context"):
                self.full_context.append({"role": meta.get("meta_title"), "content": meta.get("meta_context")})

        if thinking:
            self.full_context.append({"role": "assistant_thinking", "content": thinking})

        if meta and meta.get("thinking_time", -1) > 0:
            self.full_context.append({
                "role": "assistant_thinking_time",
                "content": round(float(meta["thinking_time"]), 2),
            })

        if original_content and original_content != content:
            self.full_context.append({"role": "assistant_original_answer", "content": original_content})

        self.full_context.append({"role": "assistant_answer", "content": content})
        self._auto_clean_context()

    def _append_ordered_assistant_message(
        self,
        *,
        model_name: str,
        ordered_blocks: list[dict],
        history_messages: list[dict],
    ) -> None:
        if model_name:
            self.full_context.append({"role": "model", "content": model_name})

        pending_history = [
            dict(message)
            for message in history_messages
            if isinstance(message, dict) and str(message.get("role", "")).strip() in {"assistant", "tool"}
        ]

        for raw_block in ordered_blocks:
            if not isinstance(raw_block, dict):
                continue

            kind = str(raw_block.get("kind", "")).strip().lower()
            if kind == "thinking":
                thinking_text = str(raw_block.get("content", "") or "")
                block_record = {"role": "assistant_thinking", "content": thinking_text}

                thinking_time = raw_block.get("thinking_time")
                if isinstance(thinking_time, (int, float)) and thinking_time > 0:
                    block_record["thinking_time"] = round(float(thinking_time), 2)

                assistant_questions = raw_block.get("assistant_questions")
                if isinstance(assistant_questions, list) and assistant_questions:
                    block_record["assistant_questions"] = list(assistant_questions)

                user_inputs = raw_block.get("user_inputs")
                if isinstance(user_inputs, list) and user_inputs:
                    block_record["user_inputs"] = list(user_inputs)

                if (
                    block_record.get("content")
                    or block_record.get("thinking_time")
                    or block_record.get("assistant_questions")
                    or block_record.get("user_inputs")
                ):
                    self.full_context.append(block_record)
                continue

            if kind == "process":
                self._append_pending_empty_tool_rounds(pending_history)
                process_payload = self._normalize_process_payload(raw_block.get("content"))
                if process_payload:
                    self.full_context.append({"role": "assistant_process", "content": process_payload})
                continue

            if kind != "answer":
                continue

            answer_text = str(raw_block.get("content", "") or "")
            matched_round = self._consume_matching_tool_round(pending_history, answer_text)
            if matched_round is not None:
                self.full_context.append(matched_round["assistant"])
                self.full_context.extend(matched_round["tools"])
                continue

            if answer_text:
                self.full_context.append({"role": "assistant_answer", "content": answer_text})

        self._append_pending_empty_tool_rounds(pending_history)
        while pending_history:
            leftover = pending_history.pop(0)
            if str(leftover.get("role", "")).strip() == "assistant" and leftover.get("tool_calls"):
                stored = dict(leftover)
                stored["role"] = "assistant_tool_calls"
                self.full_context.append(stored)
                continue
            self.full_context.append(dict(leftover))

    def _append_pending_empty_tool_rounds(self, pending_history: list[dict]) -> None:
        while True:
            next_round = self._consume_matching_tool_round(pending_history, "")
            if next_round is None:
                return
            self.full_context.append(next_round["assistant"])
            self.full_context.extend(next_round["tools"])

    def _consume_matching_tool_round(self, pending_history: list[dict], answer_text: str) -> dict | None:
        if not pending_history:
            return None

        first = pending_history[0]
        if str(first.get("role", "")).strip() != "assistant" or not first.get("tool_calls"):
            return None

        assistant_text = self._normalize_assistant_text_for_match(first.get("content", ""))
        answer_text_normalized = self._normalize_assistant_text_for_match(answer_text)
        if assistant_text != answer_text_normalized:
            return None

        assistant_message = dict(pending_history.pop(0))
        tool_messages = []
        while pending_history and str(pending_history[0].get("role", "")).strip() == "tool":
            tool_messages.append(dict(pending_history.pop(0)))

        assistant_record = dict(assistant_message)
        assistant_record["role"] = "assistant_tool_calls"
        return {
            "assistant": assistant_record,
            "tools": tool_messages,
        }

    def _normalize_assistant_text_for_match(self, value: str) -> str:
        return str(value or "").strip()

    def _normalize_process_payload(self, payload) -> dict:
        if not isinstance(payload, dict):
            return {}

        normalized: dict = {}
        list_keys = {
            "enabled_tools",
            "search_keywords",
            "uris",
            "ocr_results",
            "tool_call_history",
            "system_messages",
        }
        for key, value in payload.items():
            if key in list_keys:
                values = value if isinstance(value, list) else [value]
                cleaned_values = [item for item in values if item not in (None, "", [], {})]
                if cleaned_values:
                    normalized[key] = cleaned_values
                continue

            if value in (None, "", [], {}):
                continue
            normalized[key] = value
        return normalized

    def rollback_last_user_message(self):
        has_pending_user = bool(self.history and self.history[-1].get("role") == "user")
        if not has_pending_user:
            return

        self.history.pop()

        rollback_start = -1
        for idx in range(len(self.full_context) - 1, -1, -1):
            message = self.full_context[idx]
            if isinstance(message, dict) and message.get("role") == "epoch_count":
                rollback_start = idx
                break

        if rollback_start >= 0:
            self.full_context = self.full_context[:rollback_start]
            return

        rollback_roles = {"user", "user_original", "image_uploaded", "enabled_tools"}
        while self.full_context:
            tail = self.full_context[-1]
            role = str(tail.get("role", "")) if isinstance(tail, dict) else ""
            if role not in rollback_roles:
                break
            self.full_context.pop()

    def get_history(self) -> list:
        return self.history.copy()

    def _collect_turn_ranges(self) -> list[dict]:
        turn_ranges = []
        pending_start = None
        current_start = None
        current_last_user = ""

        def flush_turn(end_index: int):
            nonlocal current_start, current_last_user
            if current_start is None:
                return
            turn_ranges.append({
                "start": current_start,
                "end": end_index,
                "last_user": current_last_user,
            })
            current_start = None
            current_last_user = ""

        for idx, message in enumerate(self.full_context):
            if not isinstance(message, dict):
                continue

            role = str(message.get("role", ""))
            if role in {"directions", "system"}:
                flush_turn(idx)
                pending_start = None
                continue

            if role == "epoch_count":
                flush_turn(idx)
                pending_start = idx
                continue

            if role in self._TURN_LEADING_ROLES:
                flush_turn(idx)
                if pending_start is None:
                    pending_start = idx
                continue

            if role == "user":
                flush_turn(idx)
                current_start = pending_start if pending_start is not None else idx
                pending_start = None
                current_last_user = str(message.get("content", ""))
                continue

            if current_start is None:
                current_start = pending_start if pending_start is not None else idx
                pending_start = None

        flush_turn(len(self.full_context))
        return turn_ranges

    def _rewrite_epoch_markers(self, turn_ranges: list[dict]):
        epoch_markers = {turn["start"]: str(index) for index, turn in enumerate(turn_ranges, start=1)}
        normalized_context = []

        for idx, message in enumerate(self.full_context):
            if idx in epoch_markers:
                normalized_context.append({"role": "epoch_count", "content": epoch_markers[idx]})

            if not isinstance(message, dict):
                normalized_context.append(message)
                continue

            if str(message.get("role", "")) == "epoch_count":
                continue

            normalized_context.append(dict(message))

        self.full_context = normalized_context

    def _rebuild_history_from_full_context(self):
        rebuilt_history = []

        for message in self.full_context:
            if not isinstance(message, dict):
                continue

            role = str(message.get("role", ""))
            content = message.get("content", "")
            if role in self._HISTORY_ROLES:
                rebuilt_history.append(dict(message))
            elif role == "assistant_tool_calls":
                assistant_record = dict(message)
                assistant_record["role"] = "assistant"
                rebuilt_history.append(assistant_record)
            elif role == "assistant_answer":
                rebuilt_history.append({"role": "assistant", "content": content})

        self.history = rebuilt_history

    def _refresh_context_views(self) -> list[dict]:
        turn_ranges = self._collect_turn_ranges()
        self._rewrite_epoch_markers(turn_ranges)
        self._rebuild_history_from_full_context()
        return self._collect_turn_ranges()

    def _calc_token_count_for_messages(self, messages: list[dict]) -> int:
        count = 0
        for msg in messages:
            for char in str(msg.get("content", "")):
                count += 0.6 if ord(char) > 127 else 0.3
        return int(count)

    def _calc_token_count(self) -> int:
        return self._calc_token_count_for_messages(self.history)

    def _auto_clean_context(self):
        turn_ranges = self._refresh_context_views()
        while self._calc_token_count() >= 128000 and len(turn_ranges) > 1:
            oldest_turn = turn_ranges[0]
            del self.full_context[oldest_turn["start"]:oldest_turn["end"]]
            turn_ranges = self._refresh_context_views()

    def fork_to(self, epoch: int = 0) -> str:
        if epoch <= 0:
            return ""

        turn_ranges = self._refresh_context_views()
        if not turn_ranges:
            return ""

        keep_count = min(epoch, len(turn_ranges))
        keep_until = turn_ranges[keep_count - 1]["end"]
        last_user = turn_ranges[keep_count - 1]["last_user"]
        self.full_context = self.full_context[:keep_until]
        self._refresh_context_views()
        return last_user

    def _is_model_switch_prompt(self, content: str) -> bool:
        text = str(content or "")
        return (
            "回答模型已从" in text
            and "你不能继承的是" in text
            and "如果历史内容与你当前身份冲突" in text
        )

    def switch_model(self, new_model_name: str, old_model_name: str):
        prompt = prompts.Prompts.get_model_change_prompt(new_model_name, old_model_name)
        self.history = [
            msg
            for msg in self.history
            if not (
                isinstance(msg, dict)
                and msg.get("role") == "system"
                and self._is_model_switch_prompt(str(msg.get("content", "")))
            )
        ]
        self.history.append({"role": "system", "content": prompt})
        self.full_context = [
            msg
            for msg in self.full_context
            if not (
                isinstance(msg, dict)
                and msg.get("role") == "system"
                and self._is_model_switch_prompt(str(msg.get("content", "")))
            )
        ]
        self.full_context.append({"role": "system", "content": prompt})

    def _sanitize_save_name(self, raw_name: str) -> str:
        safe_title = os.path.basename(str(raw_name or "").strip())
        safe_title = os.path.splitext(safe_title)[0]
        safe_title = re.sub(r'[\\/*?:"<>|]', "", safe_title)
        return safe_title.strip()

    def _build_record_paths(
        self,
        basename: str,
        *,
        json_subdir: str | None = None,
        simple_json_subdir: str | None = None,
    ) -> dict[str, str]:
        records_root = "chat_result"
        paths = {
            "html": os.path.join(records_root, f"{basename}.html"),
            "legacy_json": os.path.join(records_root, f"{basename}.json"),
            "md": os.path.join(records_root, f"{basename}.md"),
            "json": os.path.join(records_root, f"{basename}.json"),
        }
        if json_subdir:
            paths["json"] = os.path.join(records_root, json_subdir, f"{basename}.json")
        if simple_json_subdir:
            paths["simple_json"] = os.path.join(records_root, simple_json_subdir, f"{basename}.json")
        return paths

    def _save_target_exists(
        self,
        basename: str,
        *,
        save_html: bool,
        json_subdir: str | None = None,
        save_simple_json: bool = False,
        simple_json_subdir: str | None = None,
    ) -> bool:
        paths = self._build_record_paths(
            basename,
            json_subdir=json_subdir,
            simple_json_subdir=simple_json_subdir,
        )
        candidate_paths = {
            paths["legacy_json"],
            paths["md"],
            paths["json"],
        }
        if save_html:
            candidate_paths.add(paths["html"])
        if save_simple_json and paths.get("simple_json"):
            candidate_paths.add(paths["simple_json"])
        return any(os.path.exists(path) for path in candidate_paths)

    def _resolve_save_basename(
        self,
        title: str,
        timestamp: bool = False,
        basename: str | None = None,
        overwrite: bool = False,
        *,
        save_html: bool,
        json_subdir: str | None = None,
        save_simple_json: bool = False,
        simple_json_subdir: str | None = None,
    ) -> str:
        resolved_name = self._sanitize_save_name(basename) if basename else self._sanitize_save_name(title)
        if resolved_name and timestamp:
            resolved_name += "_" + datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        if not resolved_name:
            resolved_name = "chat_" + datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

        if overwrite:
            return resolved_name

        counter = 1
        candidate = resolved_name
        while self._save_target_exists(
            candidate,
            save_html=save_html,
            json_subdir=json_subdir,
            save_simple_json=save_simple_json,
            simple_json_subdir=simple_json_subdir,
        ):
            candidate = f"{resolved_name}({counter})"
            counter += 1
        return candidate

    def _build_simple_full_context(self) -> list:
        simple_context = []
        for item in self.full_context:
            if not isinstance(item, dict):
                simple_context.append(item)
                continue

            role = str(item.get("role", "")).strip()
            if role == "tool":
                continue

            if role == "assistant_tool_calls":
                simple_context.append({"role": "assistant_answer", "content": item.get("content", "")})
                continue

            simple_context.append(item)
        return simple_context

    def save_to_disk(
        self,
        title: str,
        timestamp: bool = False,
        save_html: bool = True,
        overwrite: bool = False,
        basename: str | None = None,
        *,
        json_subdir: str | None = None,
        save_simple_json: bool = False,
        simple_json_subdir: str | None = None,
    ) -> str:
        resolved_basename = self._resolve_save_basename(
            title=title,
            timestamp=timestamp,
            basename=basename,
            overwrite=overwrite,
            save_html=save_html,
            json_subdir=json_subdir,
            save_simple_json=save_simple_json,
            simple_json_subdir=simple_json_subdir,
        )

        paths = self._build_record_paths(
            resolved_basename,
            json_subdir=json_subdir,
            simple_json_subdir=simple_json_subdir,
        )
        os.makedirs(os.path.dirname(paths["json"]), exist_ok=True)
        os.makedirs(os.path.dirname(paths["html"]), exist_ok=True)

        json_filepath = paths["json"]
        with open(json_filepath, "w", encoding="utf-8") as f:
            json.dump(self.full_context, f, ensure_ascii=False, indent=2)

        if save_simple_json and paths.get("simple_json"):
            simple_json_filepath = str(paths["simple_json"])
            os.makedirs(os.path.dirname(simple_json_filepath), exist_ok=True)
            with open(simple_json_filepath, "w", encoding="utf-8") as f:
                json.dump(self._build_simple_full_context(), f, ensure_ascii=False, indent=2)

        if not save_html:
            return json_filepath

        html_filepath = paths["html"]
        html_title = self._sanitize_save_name(title) or resolved_basename
        html_content = render_chat_archive_html(self.full_context, html_title)
        with open(html_filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        return html_filepath
