import json
import os
import re
from datetime import datetime

import tools.auto_asker as auto_asker
import tools.prompts as prompts
from tools.chat_archive_renderer import render_chat_archive_html


class ChatSession:
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
    ):
        self.history.append({"role": "assistant", "content": content})

        if model_name:
            self.full_context.append({"role": "model", "content": model_name})

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

    def rollback_last_user_message(self):
        has_pending_user = bool(self.history and self.history[-1].get("role") == "user")
        if not has_pending_user:
            return

        self.history.pop()

        # 优先按 epoch_count 回滚当前轮次，避免在首轮失败时误删 directions/system。
        rollback_start = -1
        for idx in range(len(self.full_context) - 1, -1, -1):
            message = self.full_context[idx]
            if isinstance(message, dict) and message.get("role") == "epoch_count":
                rollback_start = idx
                break

        if rollback_start >= 0:
            self.full_context = self.full_context[:rollback_start]
            return

        # 兼容旧记录：若没有 epoch 标记，仅移除本轮用户侧尾部条目。
        rollback_roles = {"user", "user_original", "image_uploaded", "enabled_tools"}
        while self.full_context:
            tail = self.full_context[-1]
            role = str(tail.get("role", "")) if isinstance(tail, dict) else ""
            if role not in rollback_roles:
                break
            self.full_context.pop()

    def get_history(self) -> list:
        return self.history.copy()

    def _calc_token_count(self) -> int:
        count = 0
        for msg in self.history:
            for char in str(msg.get("content", "")):
                count += 0.6 if ord(char) > 127 else 0.3
        return int(count)

    def _auto_clean_context(self):
        while self._calc_token_count() >= 128000 and len(self.history) > 3:
            self.history = [self.history[0]] + self.history[3:]

    def fork_to(self, epoch: int = 0) -> str:
        if epoch <= 0:
            return
        ret = ""
        new_history = []
        new_full_context = []
        for msg in self.full_context:
            if msg["role"] == "epoch_count" and int(msg["content"]) >= epoch + 1:
                break
            new_full_context.append(msg)

            role = str(msg.get("role", ""))
            content = msg.get("content", "")
            if role in ["user", "system", "assistant"]:
                new_history.append({"role": role, "content": content})
                ret = content if role == "user" else ret
                continue

            # 历史导出中助手正式回答记录为 assistant_answer，fork 后需要映射回 history 的 assistant。
            if role == "assistant_answer":
                new_history.append({"role": "assistant", "content": content})
        self.history = new_history
        self.full_context = new_full_context
        return ret

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

    def _sanitize_save_name(self, raw_name: str) -> str:
        safe_title = os.path.basename(str(raw_name or "").strip())
        safe_title = os.path.splitext(safe_title)[0]
        safe_title = re.sub(r'[\\/*?:"<>|]', "", safe_title)
        return safe_title.strip()

    def _resolve_save_filepath(
        self,
        title: str,
        timestamp: bool = False,
        basename: str | None = None,
        overwrite: bool = False,
    ) -> str:
        resolved_name = self._sanitize_save_name(basename) if basename else self._sanitize_save_name(title)
        if resolved_name and timestamp:
            resolved_name += "_" + datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        if not resolved_name:
            resolved_name = "chat_" + datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

        os.makedirs("chat_result", exist_ok=True)
        base_filepath = os.path.join("chat_result", resolved_name)
        if overwrite:
            return base_filepath

        counter = 1
        filepath = base_filepath
        while os.path.exists(f"{filepath}.json") or os.path.exists(f"{filepath}.html"):
            filepath = f"{base_filepath}({counter})"
            counter += 1
        return filepath

    def save_to_disk(
        self,
        title: str,
        timestamp: bool = False,
        save_html: bool = True,
        overwrite: bool = False,
        basename: str | None = None,
    ) -> str:
        filepath = self._resolve_save_filepath(
            title=title,
            timestamp=timestamp,
            basename=basename,
            overwrite=overwrite,
        )

        json_filepath = f"{filepath}.json"
        with open(json_filepath, "w", encoding="utf-8") as f:
            json.dump(self.full_context, f, ensure_ascii=False, indent=2)

        if not save_html:
            return json_filepath

        html_filepath = f"{filepath}.html"
        html_title = self._sanitize_save_name(title) or os.path.basename(filepath)
        html_content = render_chat_archive_html(self.full_context, html_title)
        with open(html_filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        return html_filepath
