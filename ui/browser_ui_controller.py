from __future__ import annotations

import ast
import html
import json
import math
import mimetypes
import os
import queue
import re
import shutil
import threading
import uuid
from datetime import datetime
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, quote, urlparse

import tools.prompts as prompts
import tools.reader as history_reader
from core.llm_factory import LLMFactory
from core.session import ChatSession
from tools.chat_archive_renderer import (
    _build_render_structure,
    _render_markdown_block,
    _render_system_panel,
    _render_turn,
)
from tools.documents_reader import DocumentParser, UnsupportedFileFormatError
from tools.title_generator import generate_auto_title
from ui.browser_mode import BrowserCSSMixin, BrowserIndexPageMixin, BrowserJSMixin, BrowserSessionState


class BrowserUIController(BrowserIndexPageMixin, BrowserCSSMixin, BrowserJSMixin):
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
    THEME_OPTIONS = [
        {"id": "orange", "label": "橙色", "swatch": "#d97757"},
        {"id": "green", "label": "绿色", "swatch": "#2d8a63"},
        {"id": "blue", "label": "蓝色", "swatch": "#2f6fca"},
        {"id": "black", "label": "黑色", "swatch": "#2c2c2c"},
    ]
    ACCENT_OPTIONS = [
        {"id": "orange", "label": "橙色", "swatch": "#d97757", "start": "#e28f6d", "end": "#d97757"},
        {"id": "green", "label": "绿色", "swatch": "#2d8a63", "start": "#46a979", "end": "#2d8a63"},
        {"id": "blue", "label": "蓝色", "swatch": "#2f6fca", "start": "#4d89de", "end": "#2f6fca"},
        {"id": "graphite", "label": "石墨", "swatch": "#4a4a4a", "start": "#626262", "end": "#363636"},
    ]
    BROWSER_PREF_DEFAULTS = {
        "collapse_thinking_by_default": True,
        "collapse_process_meta_by_default": True,
        "auto_collapse_output_meta": False,
        "localized_save": True,
    }

    def __init__(self, project_root: str, config: dict[str, Any]):
        self.project_root = os.path.abspath(project_root)
        self.config_path = os.path.join(self.project_root, "config.json")
        self.keys = config.get("api_keys", {})
        settings = config.get("settings", {})
        self.default_temperature = settings.get("default_temperature", 1.0)
        self.enable_system_prompt = settings.get("enable_system_prompt", True)
        self.model_catalog = self._build_model_catalog()
        default_model = settings.get("default_model", "deepseek")
        self.default_model = default_model if self._model_exists(default_model) else "deepseek"
        configured_theme = str(settings.get("browser_theme", "orange") or "orange").strip().lower()
        self.browser_theme = configured_theme if self._theme_exists(configured_theme) else "orange"
        self.browser_accent = self._resolve_browser_accent(
            self.browser_theme,
            settings.get("browser_accent"),
        )
        self.browser_preferences = self._load_browser_preferences(settings)
        self.sessions: dict[str, BrowserSessionState] = {}
        self.sessions_lock = threading.Lock()
        self.config_lock = threading.Lock()

    def serve(self, host: str, port: int) -> None:
        controller = self

        class BrowserRequestHandler(BaseHTTPRequestHandler):
            server_version = "NeoDSBrowser/1.0"

            def do_GET(self) -> None:
                controller.handle_get(self)

            def do_POST(self) -> None:
                controller.handle_post(self)

            def log_message(self, format_str: str, *args: Any) -> None:
                return

        with ThreadingHTTPServer((host, port), BrowserRequestHandler) as server:
            print(f"[Browser] 独立网页模式已启动: http://{host}:{port}")
            print("[Browser] 按 Ctrl+C 停止服务。")
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                print("\n[Browser] 服务已停止。")

    def handle_get(self, handler: BaseHTTPRequestHandler) -> None:
        parsed = urlparse(handler.path)
        if parsed.path == "/":
            self._send_html(handler, self._build_index_html())
            return
        if parsed.path == "/api/records":
            self._handle_records_request(handler)
            return
        if parsed.path == "/api/file":
            self._handle_file_request(handler, parsed)
            return
        self._send_json(handler, {"error": "Not found"}, status=404)

    def handle_post(self, handler: BaseHTTPRequestHandler) -> None:
        parsed = urlparse(handler.path)
        if parsed.path == "/api/session/new":
            session = self._create_session()
            self._send_json(
                handler,
                {
                    "session_id": session["session_id"],
                    "title": session["title"],
                    "context_tokens": session.get("context_tokens", 0.0),
                    "context_messages": session.get("context_messages", []),
                    "total_tokens": session.get("total_tokens", 0),
                    "latest_assistant_thinking": session.get("latest_assistant_thinking", ""),
                    "default_model": self.default_model,
                },
            )
            return
        if parsed.path == "/api/session/save":
            payload = self._read_json_body(handler)
            session_id = str(payload.get("session_id", "")).strip()
            self._handle_save_request(handler, session_id)
            return
        if parsed.path == "/api/session/load":
            payload = self._read_json_body(handler)
            session_id = str(payload.get("session_id", "")).strip()
            filename = str(payload.get("filename", "")).strip()
            self._handle_load_request(handler, session_id, filename)
            return
        if parsed.path == "/api/session/fork":
            payload = self._read_json_body(handler)
            session_id = str(payload.get("session_id", "")).strip()
            fork_epoch = payload.get("fork_epoch")
            self._handle_fork_request(handler, session_id, fork_epoch)
            return
        if parsed.path == "/api/session/token-usage":
            payload = self._read_json_body(handler)
            session_id = str(payload.get("session_id", "")).strip()
            self._handle_token_usage_request(handler, session_id)
            return
        if parsed.path == "/api/settings/theme":
            payload = self._read_json_body(handler)
            self._handle_theme_update_request(handler, payload)
            return
        if parsed.path == "/api/settings/browser":
            payload = self._read_json_body(handler)
            self._handle_browser_preferences_update_request(handler, payload)
            return
        if parsed.path == "/api/records/archive":
            payload = self._read_json_body(handler)
            session_id = str(payload.get("session_id", "")).strip()
            basename = payload.get("basename")
            self._handle_archive_record_request(handler, session_id, basename)
            return
        if parsed.path == "/api/records/delete":
            payload = self._read_json_body(handler)
            session_id = str(payload.get("session_id", "")).strip()
            basename = payload.get("basename")
            self._handle_delete_record_request(handler, session_id, basename)
            return
        if parsed.path == "/api/chat":
            request_payload, attachments = self._parse_chat_request(handler)
            self._stream_chat_response(handler, request_payload, attachments)
            return
        self._send_json(handler, {"error": "Not found"}, status=404)

    def _create_session(self) -> dict[str, Any]:
        session_id = uuid.uuid4().hex
        system_prompt = prompts.Prompts.universe_task_prompt
        session = ChatSession(
            system_prompt=system_prompt,
            first_time=True,
            enable_system_prompt=self.enable_system_prompt,
        )
        state = BrowserSessionState(
            session=session,
            temperature=self.default_temperature,
            selected_model=self.default_model,
        )
        with self.sessions_lock:
            self.sessions[session_id] = state
        return {
            "session_id": session_id,
            "title": "新对话",
            "context_tokens": self._estimate_context_tokens(session.get_history()),
            "context_messages": self._serialize_context_messages(session.get_history()),
            "total_tokens": self._estimate_total_tokens(session),
            "latest_assistant_thinking": "",
        }

    def _get_session_state(self, session_id: str) -> BrowserSessionState:
        with self.sessions_lock:
            state = self.sessions.get(session_id)
        if not state:
            raise KeyError("会话不存在，请新建一个浏览器会话。")
        return state

    def _handle_save_request(self, handler: BaseHTTPRequestHandler, session_id: str) -> None:
        if not session_id:
            self._send_json(handler, {"error": "缺少 session_id"}, status=400)
            return

        try:
            state = self._get_session_state(session_id)
        except KeyError as exc:
            self._send_json(handler, {"error": str(exc)}, status=404)
            return

        with state.lock:
            save_result = self._save_browser_session_snapshot(state, force_json_only=False)

        self._send_json(handler, save_result)

    def _handle_load_request(self, handler: BaseHTTPRequestHandler, session_id: str, filename: str) -> None:
        if not session_id:
            self._send_json(handler, {"error": "缺少 session_id"}, status=400)
            return
        if not filename:
            self._send_json(handler, {"error": "缺少 filename"}, status=400)
            return

        safe_filename = os.path.basename(filename)
        if safe_filename != filename:
            self._send_json(handler, {"error": "非法 filename"}, status=400)
            return

        try:
            state = self._get_session_state(session_id)
        except KeyError as exc:
            self._send_json(handler, {"error": str(exc)}, status=404)
            return

        try:
            messages, temperature, full_history = history_reader.read_from_history(safe_filename)
        except Exception as exc:
            self._send_json(handler, {"error": f"导入记录失败：{exc}"}, status=400)
            return

        if not isinstance(messages, list) or not isinstance(full_history, list):
            self._send_json(handler, {"error": "记录格式不正确，无法导入。"}, status=400)
            return

        with state.lock:
            state.session.history = list(messages)
            state.session.full_context = list(full_history)
            state.temperature = float(temperature) if isinstance(temperature, (int, float)) else self.default_temperature
            state.epoch = self._extract_loaded_epoch(full_history)
            state.title = os.path.splitext(safe_filename)[0]
            state.saved_basename = os.path.splitext(safe_filename)[0]
            loaded_model = self._extract_loaded_model(full_history)
            if loaded_model:
                state.selected_model = loaded_model

        self._send_json(
            handler,
            {
                "title": state.title or "新对话",
                "conversation_html": self._render_loaded_conversation(full_history),
                "selected_model": state.selected_model,
                "loaded_filename": safe_filename,
                "saved_basename": state.saved_basename,
                "context_tokens": self._estimate_context_tokens(state.session.get_history()),
                "context_messages": self._serialize_context_messages(state.session.get_history()),
                "total_tokens": self._estimate_total_tokens(state.session),
                "latest_assistant_thinking": self._extract_latest_assistant_thinking(state.session.full_context),
            },
        )

    def _handle_records_request(self, handler: BaseHTTPRequestHandler) -> None:
        self._send_json(handler, {"records": self._list_saved_records()})

    def _estimate_text_tokens(self, value: Any) -> int:
        if value is None:
            return 0
        if isinstance(value, dict):
            return self._estimate_text_tokens(value.get("content", ""))
        if isinstance(value, (list, tuple)):
            return sum(self._estimate_text_tokens(item) for item in value)

        total = 0.0
        for char in str(value):
            total += 0.3 if ord(char) <= 127 else 0.6
        return int(math.ceil(total))

    def _estimate_context_tokens(self, messages: list[dict[str, Any]], pending_user_text: str = "") -> int:
        total = 0
        for message in messages:
            if not isinstance(message, dict):
                continue
            if str(message.get("role", "")).strip() not in {"system", "assistant", "user"}:
                continue
            total += self._estimate_text_tokens(message.get("content", ""))
        if pending_user_text:
            total += self._estimate_text_tokens(pending_user_text)
        return int(total)

    def _estimate_total_tokens(self, session: ChatSession) -> int:
        # 总对话估算 = 正文上下文 + 思考内容（assistant_thinking）。
        history_tokens = self._estimate_context_tokens(session.get_history())
        thinking_tokens = 0
        for message in session.full_context:
            if not isinstance(message, dict):
                continue
            if str(message.get("role", "")).strip() != "assistant_thinking":
                continue
            thinking_tokens += self._estimate_text_tokens(message.get("content", ""))
        return int(history_tokens + thinking_tokens)

    def _serialize_context_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, str]]:
        serialized: list[dict[str, str]] = []
        for message in messages:
            if not isinstance(message, dict):
                continue
            role = str(message.get("role", "")).strip()
            if role not in {"system", "assistant", "user"}:
                continue
            serialized.append(
                {
                    "role": role,
                    "content": str(message.get("content", "") or ""),
                }
            )
        return serialized

    def _extract_latest_assistant_thinking(self, messages: list[dict[str, Any]]) -> str:
        for message in reversed(messages or []):
            if not isinstance(message, dict):
                continue
            if str(message.get("role", "")).strip() != "assistant_thinking":
                continue
            content = str(message.get("content", "") or "").strip()
            if content:
                return content
        return ""

    def _normalize_record_basename(self, raw_basename: Any) -> str:
        basename = os.path.basename(str(raw_basename or "").strip())
        basename = os.path.splitext(basename)[0]
        basename = re.sub(r'[\\/*?:"<>|]', "", basename)
        return basename.strip()

    def _list_record_file_paths(self, basename: str) -> list[str]:
        records_dir = os.path.join(self.project_root, "chat_result")
        if not basename or not os.path.isdir(records_dir):
            return []

        allowed_suffixes = {".json", ".html", ".md"}
        matched_paths: list[str] = []
        for item in os.scandir(records_dir):
            if not item.is_file():
                continue
            item_basename, suffix = os.path.splitext(item.name)
            if item_basename != basename or suffix.lower() not in allowed_suffixes:
                continue
            matched_paths.append(item.path)
        return sorted(matched_paths)

    def _build_unique_record_target(self, directory: str, filename: str) -> str:
        stem, suffix = os.path.splitext(filename)
        candidate = os.path.join(directory, filename)
        counter = 1
        while os.path.exists(candidate):
            candidate = os.path.join(directory, f"{stem}({counter}){suffix}")
            counter += 1
        return candidate

    def _clear_saved_basename_refs(self, basename: str) -> None:
        with self.sessions_lock:
            session_states = list(self.sessions.values())
        for state in session_states:
            with state.lock:
                if state.saved_basename == basename:
                    state.saved_basename = ""

    def _resolve_session_for_record_action(self, session_id: str) -> BrowserSessionState | None:
        if not session_id:
            return None
        return self._get_session_state(session_id)

    def _handle_archive_record_request(self, handler: BaseHTTPRequestHandler, session_id: str, basename: Any) -> None:
        safe_basename = self._normalize_record_basename(basename)
        if not safe_basename:
            self._send_json(handler, {"error": "缺少 basename"}, status=400)
            return

        try:
            state = self._resolve_session_for_record_action(session_id)
        except KeyError as exc:
            self._send_json(handler, {"error": str(exc)}, status=404)
            return

        record_paths = self._list_record_file_paths(safe_basename)
        if not record_paths:
            self._send_json(handler, {"error": "未找到可归档的记录文件"}, status=404)
            return

        archive_dir = os.path.join(self.project_root, "chat_result", "filed")
        os.makedirs(archive_dir, exist_ok=True)

        archived_files: list[str] = []
        try:
            for source_path in record_paths:
                target_path = self._build_unique_record_target(archive_dir, os.path.basename(source_path))
                shutil.move(source_path, target_path)
                archived_files.append(os.path.basename(target_path))
        except OSError as exc:
            self._send_json(handler, {"error": f"归档失败：{exc}"}, status=500)
            return

        self._clear_saved_basename_refs(safe_basename)
        saved_basename = ""
        if state is not None:
            with state.lock:
                saved_basename = state.saved_basename

        self._send_json(
            handler,
            {
                "basename": safe_basename,
                "archived_files": archived_files,
                "saved_basename": saved_basename,
            },
        )

    def _handle_delete_record_request(self, handler: BaseHTTPRequestHandler, session_id: str, basename: Any) -> None:
        safe_basename = self._normalize_record_basename(basename)
        if not safe_basename:
            self._send_json(handler, {"error": "缺少 basename"}, status=400)
            return

        try:
            state = self._resolve_session_for_record_action(session_id)
        except KeyError as exc:
            self._send_json(handler, {"error": str(exc)}, status=404)
            return

        record_paths = self._list_record_file_paths(safe_basename)
        if not record_paths:
            self._send_json(handler, {"error": "未找到可删除的记录文件"}, status=404)
            return

        deleted_files: list[str] = []
        try:
            for source_path in record_paths:
                os.remove(source_path)
                deleted_files.append(os.path.basename(source_path))
        except OSError as exc:
            self._send_json(handler, {"error": f"删除失败：{exc}"}, status=500)
            return

        self._clear_saved_basename_refs(safe_basename)
        saved_basename = ""
        if state is not None:
            with state.lock:
                saved_basename = state.saved_basename

        self._send_json(
            handler,
            {
                "basename": safe_basename,
                "deleted_files": deleted_files,
                "saved_basename": saved_basename,
            },
        )

    def _save_browser_session_snapshot(
        self,
        state: BrowserSessionState,
        *,
        force_json_only: bool,
    ) -> dict[str, str]:
        title_hint = state.title or "新对话"
        saved_path = state.session.save_to_disk(
            title=title_hint,
            save_html=not force_json_only and bool(self.browser_preferences.get("localized_save", True)),
            overwrite=bool(state.saved_basename),
            basename=state.saved_basename or None,
        )
        state.saved_basename = os.path.splitext(os.path.basename(saved_path))[0]
        return {
            "saved_path": os.path.abspath(saved_path),
            "saved_basename": state.saved_basename,
        }

    def _handle_theme_update_request(self, handler: BaseHTTPRequestHandler, payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            self._send_json(handler, {"error": "主题设置载荷必须是对象。"}, status=400)
            return

        theme_id = self.browser_theme
        accent_id = self.browser_accent

        if "theme" in payload:
            theme_id = str(payload.get("theme", "") or "").strip().lower()
            if not self._theme_exists(theme_id):
                self._send_json(handler, {"error": "不支持的主题色。"}, status=400)
                return

        if "accent" in payload:
            accent_id = str(payload.get("accent", "") or "").strip().lower()
            if not self._accent_exists(accent_id):
                self._send_json(handler, {"error": "不支持的高亮色。"}, status=400)
                return

        theme_id = theme_id if self._theme_exists(theme_id) else self.browser_theme
        accent_id = self._resolve_browser_accent(theme_id, accent_id)

        try:
            self._persist_browser_settings({
                "browser_theme": theme_id,
                "browser_accent": accent_id,
            })
        except Exception as exc:
            self._send_json(handler, {"error": f"保存主题失败：{exc}"}, status=500)
            return

        self.browser_theme = theme_id
        self.browser_accent = accent_id
        self._send_json(handler, {"theme": theme_id, "accent": accent_id})

    def _persist_browser_settings(self, settings_updates: dict[str, Any]) -> None:
        with self.config_lock:
            config_obj: dict[str, Any] = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                    if isinstance(loaded, dict):
                        config_obj = loaded
            settings = config_obj.get("settings")
            if not isinstance(settings, dict):
                settings = {}
                config_obj["settings"] = settings
            settings.update(settings_updates)
            with open(self.config_path, "w", encoding="utf-8") as handle:
                json.dump(config_obj, handle, ensure_ascii=False, indent=4)

    def _handle_browser_preferences_update_request(
        self,
        handler: BaseHTTPRequestHandler,
        payload: dict[str, Any],
    ) -> None:
        if not isinstance(payload, dict):
            self._send_json(handler, {"error": "设置载荷必须是对象。"}, status=400)
            return

        updates: dict[str, bool] = {}
        for key in self.BROWSER_PREF_DEFAULTS:
            if key not in payload:
                continue
            value = payload.get(key)
            if not isinstance(value, bool):
                self._send_json(handler, {"error": f"{key} 必须是布尔值。"}, status=400)
                return
            updates[key] = value

        if not updates:
            self._send_json(handler, {"error": "没有可更新的设置项。"}, status=400)
            return

        try:
            self._persist_browser_settings({f"browser_{key}": value for key, value in updates.items()})
        except Exception as exc:
            self._send_json(handler, {"error": f"保存设置失败：{exc}"}, status=500)
            return

        self.browser_preferences.update(updates)
        self._send_json(handler, {"preferences": self.browser_preferences})

    def _load_browser_preferences(self, settings: dict[str, Any]) -> dict[str, bool]:
        preferences: dict[str, bool] = {}
        for key, default in self.BROWSER_PREF_DEFAULTS.items():
            raw_value = settings.get(f"browser_{key}", default)
            preferences[key] = self._coerce_bool(raw_value, default)
        return preferences

    def _coerce_bool(self, value: Any, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        return default

    def _handle_fork_request(self, handler: BaseHTTPRequestHandler, session_id: str, fork_epoch: Any) -> None:
        if not session_id:
            self._send_json(handler, {"error": "缺少 session_id"}, status=400)
            return

        try:
            target_epoch = int(fork_epoch)
        except (TypeError, ValueError):
            self._send_json(handler, {"error": "fork_epoch 必须是整数。"}, status=400)
            return

        try:
            state = self._get_session_state(session_id)
        except KeyError as exc:
            self._send_json(handler, {"error": str(exc)}, status=404)
            return

        with state.lock:
            if state.epoch <= 1:
                self._send_json(handler, {"error": "当前会话轮次不足，无法 fork。"}, status=400)
                return
            if target_epoch < 1 or target_epoch >= state.epoch:
                self._send_json(
                    handler,
                    {"error": f"无效的轮次。请输入一个介于 1 和 {state.epoch - 1} 之间的整数。"},
                    status=400,
                )
                return

            state.session.fork_to(target_epoch)
            state.epoch = target_epoch
            restored_model = self._extract_loaded_model(state.session.full_context)
            if restored_model:
                state.selected_model = restored_model

            self._send_json(
                handler,
                {
                    "title": state.title or "新对话",
                    "conversation_html": self._render_loaded_conversation(state.session.full_context),
                    "selected_model": state.selected_model,
                    "epoch": state.epoch,
                    "context_tokens": self._estimate_context_tokens(state.session.get_history()),
                    "context_messages": self._serialize_context_messages(state.session.get_history()),
                    "total_tokens": self._estimate_total_tokens(state.session),
                    "latest_assistant_thinking": self._extract_latest_assistant_thinking(state.session.full_context),
                },
            )

    def _handle_token_usage_request(self, handler: BaseHTTPRequestHandler, session_id: str) -> None:
        if not session_id:
            self._send_json(handler, {"error": "缺少 session_id"}, status=400)
            return

        try:
            state = self._get_session_state(session_id)
        except KeyError as exc:
            self._send_json(handler, {"error": str(exc)}, status=404)
            return

        with state.lock:
            stats = self._build_model_token_usage_stats(state.session)

        self._send_json(handler, stats)

    def _normalize_usage_model_name(self, raw_name: Any) -> str:
        name = str(raw_name or "").strip()
        if not name:
            return "unknown"
        if "deepseek" in name.lower():
            return "deepseek"
        return name

    def _build_model_token_usage_stats(self, session: ChatSession) -> dict[str, Any]:
        model_totals: dict[str, dict[str, int]] = {}
        conversation_input_context_tokens = 0
        active_model = ""

        for message in session.full_context:
            if not isinstance(message, dict):
                continue

            role = str(message.get("role", "")).strip()
            content = message.get("content", "")

            if role == "assistant_thinking":
                if active_model:
                    bucket = model_totals.setdefault(active_model, {"input_tokens": 0, "output_tokens": 0})
                    bucket["output_tokens"] += self._estimate_text_tokens(content)
                continue

            if role == "assistant_answer":
                if active_model:
                    bucket = model_totals.setdefault(active_model, {"input_tokens": 0, "output_tokens": 0})
                    bucket["output_tokens"] += self._estimate_text_tokens(content)
                conversation_input_context_tokens += self._estimate_text_tokens(content)
                continue

            if role in {"system", "user", "assistant"}:
                conversation_input_context_tokens += self._estimate_text_tokens(content)
                continue

            if role == "model":
                active_model = self._normalize_usage_model_name(content)
                bucket = model_totals.setdefault(active_model, {"input_tokens": 0, "output_tokens": 0})
                bucket["input_tokens"] += conversation_input_context_tokens
                continue

        model_stats = []
        total_input = 0
        total_output = 0
        for model_name, token_info in model_totals.items():
            input_tokens = int(token_info.get("input_tokens", 0))
            output_tokens = int(token_info.get("output_tokens", 0))
            total_input += input_tokens
            total_output += output_tokens
            model_stats.append(
                {
                    "model": model_name,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                }
            )

        model_stats.sort(
            key=lambda item: int(item.get("input_tokens", 0)) + int(item.get("output_tokens", 0)),
            reverse=True,
        )
        return {
            "model_stats": model_stats,
            "total_input_tokens": int(total_input),
            "total_output_tokens": int(total_output),
            "total_tokens": int(total_input + total_output),
        }

    def _list_saved_records(self, limit: int = 200) -> list[dict[str, Any]]:
        records_dir = os.path.join(self.project_root, "chat_result")
        if not os.path.isdir(records_dir):
            return []

        allowed_suffixes = {".json", ".html", ".md"}
        format_order = {"json": 0, "html": 1, "md": 2}
        grouped_entries: dict[str, dict[str, Any]] = {}

        for item in os.scandir(records_dir):
            if not item.is_file():
                continue

            base_name, suffix = os.path.splitext(item.name)
            suffix = suffix.lower()
            if suffix not in allowed_suffixes:
                continue

            try:
                stat = item.stat()
            except OSError:
                continue

            modified_at = datetime.fromtimestamp(stat.st_mtime)
            entry = grouped_entries.setdefault(
                base_name,
                {
                    "title": base_name,
                    "basename": base_name,
                    "modified_at": modified_at.isoformat(timespec="seconds"),
                    "modified_label": modified_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "files": [],
                    "_sort_ts": 0.0,
                },
            )
            if stat.st_mtime >= float(entry["_sort_ts"]):
                entry["modified_at"] = modified_at.isoformat(timespec="seconds")
                entry["modified_label"] = modified_at.strftime("%Y-%m-%d %H:%M:%S")
                entry["_sort_ts"] = float(stat.st_mtime)

            entry["files"].append(
                {
                    "type": suffix.lstrip("."),
                    "label": suffix.lstrip(".").upper(),
                    "filename": item.name,
                    "url": self._browser_file_url(item.path),
                }
            )

        entries = list(grouped_entries.values())
        for entry in entries:
            files = entry.get("files", [])
            if isinstance(files, list):
                files.sort(key=lambda item: format_order.get(str(item.get("type", "")).lower(), 99))
                entry["formats"] = [str(item.get("label", "")) for item in files if item.get("label")]
                preferred_file = next(
                    (item for item in files if str(item.get("type", "")).lower() == "json"),
                    files[0] if files else None,
                )
                entry["load_filename"] = str(preferred_file.get("filename", "")) if preferred_file else ""
                entry["search_text"] = " ".join(
                    [str(entry.get("title", ""))]
                    + [str(item.get("filename", "")) for item in files]
                    + [str(item.get("type", "")) for item in files]
                ).strip()

        entries.sort(key=lambda item: float(item.get("_sort_ts", 0.0)), reverse=True)
        trimmed = entries[: max(1, limit)] if limit > 0 else entries
        for item in trimmed:
            item.pop("_sort_ts", None)
        return trimmed

    def _render_loaded_conversation(self, full_context: list[dict[str, Any]]) -> str:
        structure = _build_render_structure(full_context)
        system_html = _render_system_panel(structure.get("system_messages", []), structure.get("misc_messages", []))
        turns_html = "\n".join(_render_turn(turn) for turn in structure.get("turns", []))
        return f"{system_html}{turns_html}"

    def _extract_loaded_epoch(self, full_context: list[dict[str, Any]]) -> int:
        epoch = 0
        for item in full_context:
            if not isinstance(item, dict):
                continue
            if item.get("role") == "epoch_count":
                try:
                    epoch = max(epoch, int(item.get("content", 0)))
                except (TypeError, ValueError):
                    continue
        if epoch > 0:
            return epoch
        return sum(1 for item in full_context if isinstance(item, dict) and item.get("role") == "user")

    def _extract_loaded_model(self, full_context: list[dict[str, Any]]) -> str:
        for item in reversed(full_context):
            if not isinstance(item, dict) or item.get("role") != "model":
                continue
            model_id = str(item.get("content", "") or "").strip()
            if model_id and self._model_exists(model_id):
                return model_id
        return ""

    def _parse_chat_request(self, handler: BaseHTTPRequestHandler) -> tuple[dict[str, Any], list[Any]]:
        content_type = handler.headers.get("Content-Type", "")
        if content_type.startswith("application/json"):
            return self._read_json_body(handler), []

        body_fields, attachments = self._read_multipart_body(handler, content_type)
        raw_request = body_fields.get("request", "{}")
        try:
            request_payload = json.loads(raw_request)
        except json.JSONDecodeError:
            request_payload = {}
        return request_payload, attachments

    def _read_multipart_body(
        self,
        handler: BaseHTTPRequestHandler,
        content_type: str,
    ) -> tuple[dict[str, str], list[dict[str, Any]]]:
        content_length = int(handler.headers.get("Content-Length", "0") or 0)
        raw_body = handler.rfile.read(content_length) if content_length > 0 else b""
        if not raw_body:
            return {}, []

        message_bytes = (
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8")
            + raw_body
        )
        message = BytesParser(policy=default).parsebytes(message_bytes)

        fields: dict[str, str] = {}
        attachments: list[dict[str, Any]] = []
        for part in message.iter_parts():
            name = part.get_param("name", header="content-disposition")
            if not name:
                continue

            payload = part.get_payload(decode=True) or b""
            filename = part.get_filename()
            if filename:
                attachments.append(
                    {
                        "filename": filename,
                        "content": payload,
                    }
                )
                continue

            charset = part.get_content_charset() or "utf-8"
            fields[name] = payload.decode(charset, errors="replace")

        return fields, attachments

    def _stream_chat_response(
        self,
        handler: BaseHTTPRequestHandler,
        request_payload: dict[str, Any],
        attachments: list[Any],
    ) -> None:
        try:
            session_id = str(request_payload.get("session_id", "")).strip()
            if not session_id:
                raise ValueError("缺少 session_id。")
            state = self._get_session_state(session_id)
        except Exception as exc:
            self._send_json(handler, {"error": str(exc)}, status=400)
            return

        handler.send_response(200)
        handler.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        handler.send_header("Cache-Control", "no-cache")
        handler.send_header("Connection", "close")
        handler.end_headers()
        handler.close_connection = True

        def emit(event: dict[str, Any]) -> bool:
            try:
                line = json.dumps(event, ensure_ascii=False) + "\n"
                handler.wfile.write(line.encode("utf-8"))
                handler.wfile.flush()
                return True
            except (BrokenPipeError, ConnectionResetError):
                return False

        with state.lock:
            try:
                for event in self._chat_event_stream(state, request_payload, attachments):
                    if not emit(event):
                        break
            except Exception as exc:
                emit({"type": "error", "content": str(exc)})

    def _chat_event_stream(
        self,
        state: BrowserSessionState,
        request_payload: dict[str, Any],
        attachments: list[Any],
    ):
        selected_model = str(request_payload.get("model", self.default_model)).strip() or self.default_model
        selected_model = selected_model if self._model_exists(selected_model) else self.default_model
        previous_model = state.selected_model if self._model_exists(state.selected_model) else self.default_model
        if previous_model != selected_model:
            state.session.switch_model(selected_model, previous_model)
        state.selected_model = selected_model

        original_text = str(request_payload.get("message", "") or "")
        thinking_value = request_payload.get("thinking")
        extras = request_payload.get("extras", {})
        if not isinstance(extras, dict):
            extras = {}

        image_paths, document_sections, attachment_infos, warnings = self._persist_attachments(attachments)
        for warning in warnings:
            yield {"type": "warning", "content": warning}

        final_user_text = original_text
        if document_sections:
            final_user_text += ("\n\n" if final_user_text.strip() else "")
            final_user_text += "\n\n".join(document_sections)

        if not final_user_text.strip() and not image_paths:
            raise ValueError("消息内容为空。请输入文本，或者至少附带一个文件。")

        state.epoch += 1
        state.session.add_epoch_count(state.epoch)

        title_queue: queue.Queue[str] | None = None
        if state.epoch == 1 and not state.title and original_text.strip():
            title_queue = self._start_title_generation_task(state, original_text)

        def poll_title_event() -> dict[str, str] | None:
            generated_title = self._poll_generated_title(title_queue)
            if not generated_title:
                return None
            state.title = generated_title
            return {"type": "title", "title": state.title}

        resolved_model, extra_kwargs = self._build_model_request(
            selected_model=selected_model,
            thinking_value=thinking_value,
            extras=extras,
        )
        enabled_tools = ["web_search"] if extra_kwargs.get("enable_search") else []

        state.session.add_enabled_tools(enabled_tools)
        state.session.add_user_message(
            content=final_user_text,
            original_text=original_text if original_text != final_user_text else None,
            images=image_paths or None,
        )

        assistant_text_parts: list[str] = []
        thinking_parts: list[str] = []
        meta: dict[str, Any] = {}
        live_system_messages: list[str] = []
        live_tool_history: list[dict[str, Any]] = []
        answer_stream_started = False
        non_content_boundary_since_last_content = False

        try:
            llm_client = LLMFactory.create_client(resolved_model, self.keys)
            stream = llm_client.chat_stream(
                messages=state.session.get_history(),
                temperature=state.temperature,
                image_paths=image_paths,
                **extra_kwargs,
            )
            for chunk in stream:
                if not isinstance(chunk, dict):
                    continue

                title_event = poll_title_event()
                if title_event:
                    yield title_event

                chunk_type = chunk.get("type")
                if chunk_type == "content":
                    assistant_text_parts.append(chunk.get("content", ""))
                    answer_stream_started = True
                    non_content_boundary_since_last_content = False
                elif chunk_type == "thinking":
                    thinking_text = str(chunk.get("content", "") or "")
                    # 仅在“连续正文段”里纠偏 thinking -> content。
                    # 若中间出现 meta/system/OCR 等边界（常见于工具调用），允许重新进入 thinking。
                    if (
                        answer_stream_started
                        and not non_content_boundary_since_last_content
                        and chunk.get("display", True)
                        and thinking_text
                    ):
                        assistant_text_parts.append(thinking_text)
                        chunk = dict(chunk)
                        chunk["type"] = "content"
                    else:
                        thinking_parts.append(thinking_text)
                elif chunk_type == "meta":
                    self._merge_meta(meta, chunk)
                    non_content_boundary_since_last_content = True
                    if chunk.get("tool_call_history"):
                        live_tool_history = []
                elif chunk_type == "meta_ocr":
                    non_content_boundary_since_last_content = True
                    meta.setdefault("ocr_results", []).append(
                        {
                            "image_path": chunk.get("image_path", ""),
                            "ocr_text": chunk.get("ocr_text", ""),
                        }
                    )
                elif chunk_type == "system":
                    non_content_boundary_since_last_content = True
                    normalized_system = self._normalize_system_message(chunk.get("content", ""))
                    if normalized_system:
                        live_system_messages.append(normalized_system)
                        self._update_live_tool_history(live_tool_history, normalized_system)
                    chunk = dict(chunk)
                    chunk["content"] = normalized_system

                if chunk_type in {"meta", "meta_ocr", "system"}:
                    chunk = dict(chunk)
                    chunk["assistant_live_meta_html"] = self._render_live_assistant_activity(
                        model_name=selected_model,
                        meta=meta,
                        enabled_tools=enabled_tools,
                        live_tool_history=live_tool_history,
                        system_messages=live_system_messages,
                    )
                yield chunk

            title_event = poll_title_event()
            if title_event:
                yield title_event
        except Exception:
            state.session.rollback_last_user_message()
            if state.epoch > 0:
                state.epoch -= 1
            raise

        final_answer = "".join(assistant_text_parts).strip()
        final_thinking = "".join(thinking_parts).strip()

        if not final_answer:
            final_answer = "模型没有返回有效内容。"

        state.session.add_assistant_message(
            content=final_answer,
            thinking=final_thinking,
            model_name=selected_model,
            meta=meta,
        )

        auto_save_result: dict[str, str] | None = None
        auto_save_error = ""
        try:
            auto_save_result = self._save_browser_session_snapshot(state, force_json_only=True)
        except Exception as exc:
            auto_save_error = str(exc)

        yield {
            "type": "done",
            "title": state.title or "新对话",
            "epoch": state.epoch,
            "token_count": self._estimate_total_tokens(state.session),
            "total_tokens": self._estimate_total_tokens(state.session),
            "context_tokens": self._estimate_context_tokens(state.session.get_history()),
            "context_messages": self._serialize_context_messages(state.session.get_history()),
            "latest_assistant_thinking": final_thinking,
            "assistant_answer_text": final_answer,
            "assistant_answer_html": self._render_answer_block(final_answer),
            "assistant_meta_html": self._render_assistant_meta(
                model_name=selected_model,
                thinking=final_thinking,
                meta=meta,
                enabled_tools=enabled_tools,
            ),
            "user_html": self._render_user_block(original_text, image_paths, attachment_infos),
            "system_messages": live_system_messages,
            "saved_basename": (auto_save_result or {}).get("saved_basename", state.saved_basename),
            "saved_path": (auto_save_result or {}).get("saved_path", ""),
            "autosave_error": auto_save_error,
        }

    def _start_title_generation_task(
        self,
        state: BrowserSessionState,
        seed_text: str,
    ) -> queue.Queue[str]:
        result_queue: queue.Queue[str] = queue.Queue(maxsize=1)
        title_seed = seed_text.strip()

        def worker() -> None:
            if not title_seed:
                return
            try:
                generated_title = str(generate_auto_title(self.keys.get("deepseek", ""), title_seed) or "").strip()
            except Exception:
                return
            if not generated_title:
                return
            try:
                result_queue.put_nowait(generated_title)
            except queue.Full:
                pass

            with state.lock:
                if not state.title:
                    state.title = generated_title

        threading.Thread(target=worker, name="browser-title-generator", daemon=True).start()
        return result_queue

    def _poll_generated_title(self, title_queue: queue.Queue[str] | None) -> str:
        if not title_queue:
            return ""
        try:
            return str(title_queue.get_nowait() or "").strip()
        except queue.Empty:
            return ""

    def _persist_attachments(
        self,
        attachments: list[Any],
    ) -> tuple[list[str], list[str], list[dict[str, str]], list[str]]:
        if not attachments:
            return [], [], [], []

        upload_dir = os.path.join(
            self.project_root,
            "chat_result",
            "browser_uploads",
            datetime.now().strftime("%Y-%m-%d"),
        )
        os.makedirs(upload_dir, exist_ok=True)

        parser = DocumentParser()
        image_paths: list[str] = []
        document_sections: list[str] = []
        attachment_infos: list[dict[str, str]] = []
        warnings: list[str] = []

        for item in attachments:
            original_name = os.path.basename(str(item.get("filename", "")))
            if not original_name:
                continue

            safe_name = re.sub(r"[^\w.\-()\u4e00-\u9fff]+", "_", original_name).strip("._")
            safe_name = safe_name or f"upload_{uuid.uuid4().hex[:8]}"
            ext = os.path.splitext(safe_name)[1].lower()
            target_path = os.path.join(upload_dir, f"{uuid.uuid4().hex[:10]}_{safe_name}")

            with open(target_path, "wb") as handle:
                handle.write(item.get("content", b""))

            attachment_infos.append(
                {
                    "name": original_name,
                    "kind": "image" if ext in self.IMAGE_EXTENSIONS else "document",
                    "path": target_path,
                }
            )

            if ext in self.IMAGE_EXTENSIONS:
                image_paths.append(target_path)
                continue

            try:
                parsed_text = parser.parse(target_path)
                document_sections.append(
                    f"用户附带了文件《{original_name}》：\n<file>\n{parsed_text}\n</file>"
                )
            except UnsupportedFileFormatError as exc:
                warnings.append(str(exc))
            except Exception as exc:
                warnings.append(f"文件《{original_name}》解析失败: {exc}")

        return image_paths, document_sections, attachment_infos, warnings

    def _build_model_request(
        self,
        selected_model: str,
        thinking_value: Any,
        extras: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        extra_kwargs: dict[str, Any] = {}
        resolved_model = selected_model

        if selected_model == "deepseek":
            if thinking_value == "chat":
                resolved_model = "deepseek-chat"
            else:
                resolved_model = "deepseek-reasoner"
                if extras.get("interactive_thinking"):
                    extra_kwargs["enable_enhanced_thinking"] = True
            if extras.get("enable_search"):
                extra_kwargs["enable_search"] = True
                if resolved_model == "deepseek-chat":
                    extra_kwargs["searchEffort"] = "minimal"
                else:
                    extra_kwargs["searchEffort"] = str(extras.get("search_effort", "low"))

        elif selected_model == "deepseek-agent-preview":
            resolved_model = "deepseek-reasoner"
            extra_kwargs["enable_agent"] = True
            if extras.get("interactive_thinking"):
                extra_kwargs["enable_enhanced_thinking"] = True
            if extras.get("enable_search", True):
                extra_kwargs["enable_search"] = True
                extra_kwargs["searchEffort"] = str(extras.get("search_effort", "medium"))

        elif "gemini" in selected_model:
            extra_kwargs["think_level"] = str(thinking_value or "medium")
            extra_kwargs["enable_search"] = bool(extras.get("enable_search", False))

        elif "qwen" in selected_model:
            extra_kwargs["isQwenThinking"] = str(thinking_value or "auto")
            extra_kwargs["enable_search"] = bool(extras.get("enable_search", False))
            if extra_kwargs["enable_search"]:
                extra_kwargs["search_strategy"] = str(extras.get("search_strategy", "turbo"))

        elif "doubao" in selected_model:
            extra_kwargs["reasoningEffort"] = str(thinking_value or "medium")
            extra_kwargs["enable_search"] = bool(extras.get("enable_search", False))

        elif "kimi" in selected_model:
            extra_kwargs["enable_thinking"] = thinking_value != "disabled"
            extra_kwargs["enable_search"] = bool(extras.get("enable_search", False))

        elif "minimax" in selected_model.lower():
            extra_kwargs["enable_search"] = bool(extras.get("enable_search", False))

        return resolved_model, extra_kwargs

    def _merge_meta(self, meta: dict[str, Any], chunk: dict[str, Any]) -> None:
        list_keys = {
            "uris",
            "ocr_results",
            "search_keywords",
            "assistant_questions",
            "user_inputs",
            "tool_call_history",
        }
        for key, value in chunk.items():
            if key == "type":
                continue
            if key in list_keys:
                target = meta.setdefault(key, [])
                values = value if isinstance(value, list) else [value]
                for item in values:
                    if item not in target:
                        target.append(item)
            else:
                meta[key] = value

    def _render_live_assistant_activity(
        self,
        model_name: str,
        meta: dict[str, Any],
        enabled_tools: list[str],
        live_tool_history: list[dict[str, Any]],
        system_messages: list[str],
    ) -> str:
        sections: list[str] = []
        merged_tool_history = self._merge_live_tool_history(meta.get("tool_call_history"), live_tool_history)

        if enabled_tools:
            sections.append(self._wrap_meta_section("启用工具", self._render_chip_list(enabled_tools)))
        if meta.get("think_level"):
            sections.append(self._wrap_meta_section("思考等级", self._render_chip_list([meta["think_level"]])))
        if meta.get("search_keywords"):
            sections.append(self._wrap_meta_section("搜索关键词", self._render_chip_list(meta["search_keywords"])))
        if meta.get("uris"):
            sections.append(self._wrap_meta_section("搜索来源", self._render_link_list(meta["uris"])))
        if meta.get("ocr_results"):
            ocr_blocks = "".join(self._render_ocr_item(item) for item in meta["ocr_results"])
            sections.append(self._wrap_meta_section("OCR 提取", ocr_blocks))
        if merged_tool_history:
            sections.append(self._wrap_meta_section("工具调用", self._render_tool_history(merged_tool_history)))

        if system_messages:
            sections.append(self._wrap_meta_section("过程日志", _render_markdown_block("\n\n".join(system_messages))))

        if not sections:
            return ""

        summary = f"{model_name} 过程元数据" if model_name else "过程元数据"
        summary = f"{model_name} 过程元数据" if model_name else "过程元数据"
        return self._render_meta_details_box(summary, "".join(sections), extra_class="assistant-process-box live-log")

    def _merge_live_tool_history(self, final_history: Any, live_tool_history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        final_items = [dict(item) for item in final_history or [] if isinstance(item, dict)]
        live_items = [dict(item) for item in live_tool_history if isinstance(item, dict)]
        if not final_items:
            return live_items

        running_items = [item for item in live_items if str(item.get("status", "")) == "running"]
        return final_items + running_items

    def _normalize_system_message(self, content: Any) -> str:
        text = re.sub(r"\x1b\[[0-9;]*m", "", str(content or ""))
        return text.strip()

    def _update_live_tool_history(self, live_tool_history: list[dict[str, Any]], message: str) -> None:
        if not message:
            return

        if "请求工具" in message and "网络搜索" in message:
            tool_item = {"name": "search_web", "status": "running"}
            queries = self._extract_live_queries(message)
            if queries:
                tool_item["queries"] = queries
            self._push_live_tool_history(live_tool_history, tool_item)
            return

        if "网络搜索返回结果" in message:
            self._finish_live_tool_history(live_tool_history, "search_web", "success")
            return

        if "请求工具" in message and "内置搜索工具" in message:
            self._push_live_tool_history(live_tool_history, {"name": "$web_search", "status": "running"})
            return

        if "请求工具" in message and "提取图片文本" in message:
            tool_item = {"name": "ocr", "status": "running"}
            target_path = self._extract_live_target(message)
            if target_path:
                tool_item["target"] = target_path
            self._push_live_tool_history(live_tool_history, tool_item)
            return

        if "OCR返回结果" in message or "本地OCR返回结果" in message:
            self._finish_live_tool_history(live_tool_history, "ocr", "success")
            return

        if "请求工具" in message and "获取用户进一步输入" in message:
            self._push_live_tool_history(live_tool_history, {"name": "get_user", "status": "running"})
            return

        if "请求工具" in message and "创建工具请求" in message:
            self._push_live_tool_history(live_tool_history, {"name": "create_tool", "status": "running"})
            return

        created_tool_match = re.search(r"正在执行新创建的工具 ['\"]([^'\"]+)['\"]", message)
        if created_tool_match:
            self._push_live_tool_history(
                live_tool_history,
                {"name": created_tool_match.group(1), "status": "running"},
            )
            return

        failed_tool_match = re.search(r"工具 ['\"]([^'\"]+)['\"] 执行失败", message)
        if failed_tool_match:
            self._finish_live_tool_history(live_tool_history, failed_tool_match.group(1), "failed")
            return

        success_tool_match = re.search(r"工具 ['\"]([^'\"]+)['\"] 执行结果", message)
        if success_tool_match:
            self._finish_live_tool_history(live_tool_history, success_tool_match.group(1), "success")

    def _extract_live_queries(self, message: str) -> list[str]:
        match = re.search(r"关键词[:：]\s*(.+?)(?:\.\.\.|$)", message)
        if not match:
            return []
        raw_value = match.group(1).strip()
        try:
            parsed = ast.literal_eval(raw_value)
        except (ValueError, SyntaxError):
            parsed = None

        if isinstance(parsed, (list, tuple)):
            return [str(item).strip() for item in parsed if str(item).strip()]
        if raw_value:
            return [raw_value]
        return []

    def _extract_live_target(self, message: str) -> str:
        match = re.search(r"文本[:：]\s*(.+?)(?:\.\.\.|$)", message)
        return match.group(1).strip() if match else ""

    def _push_live_tool_history(self, live_tool_history: list[dict[str, Any]], tool_item: dict[str, Any]) -> None:
        if not tool_item.get("name"):
            return
        if live_tool_history and live_tool_history[-1].get("name") == tool_item.get("name") and live_tool_history[-1].get("status") == "running":
            live_tool_history[-1].update(tool_item)
            return
        live_tool_history.append(dict(tool_item))

    def _finish_live_tool_history(
        self,
        live_tool_history: list[dict[str, Any]],
        tool_name: str,
        status: str,
    ) -> None:
        for item in reversed(live_tool_history):
            if item.get("name") == tool_name and item.get("status") == "running":
                item["status"] = status
                return
        live_tool_history.append({"name": tool_name, "status": status})

    def _render_user_block(
        self,
        original_text: str,
        image_paths: list[str],
        attachment_infos: list[dict[str, str]],
    ) -> str:
        body = _render_markdown_block(original_text or "")
        extras: list[str] = []

        if image_paths:
            cards = []
            for path in image_paths:
                file_url = self._browser_file_url(path)
                cards.append(
                    '<div class="image-card">'
                    f'<img src="{file_url}" alt="用户上传图片">'
                    f'<a href="{file_url}" target="_blank" rel="noreferrer">{html.escape(os.path.basename(path))}</a>'
                    "</div>"
                )
            extras.append(f'<div class="image-grid">{"".join(cards)}</div>')

        document_names = [item["name"] for item in attachment_infos if item.get("kind") == "document"]
        if document_names:
            chips = "".join(f'<span class="chip">{html.escape(name)}</span>' for name in document_names)
            extras.append(
                '<div class="browser-attachment-meta">'
                '<div class="meta-title">附件</div>'
                f'<div class="chip-list">{chips}</div>'
                "</div>"
            )

        return body + "".join(extras)

    def _render_answer_block(self, answer: str) -> str:
        return _render_markdown_block(answer or "")

    def _render_assistant_meta(
        self,
        model_name: str,
        thinking: str,
        meta: dict[str, Any],
        enabled_tools: list[str],
    ) -> str:
        sections: list[str] = []
        thinking_time = meta.get("thinking_time")
        summary = model_name
        if isinstance(thinking_time, (int, float)) and thinking_time > 0:
            summary = f"{summary} 已思考 {thinking_time:.2f}s" if summary else f"已思考 {thinking_time:.2f}s"

        supplement_thread = self._render_supplement_thread(
            meta.get("assistant_questions"),
            meta.get("user_inputs"),
        )
        thinking_html_parts: list[str] = []
        if thinking:
            thinking_html_parts.append(_render_markdown_block(thinking))
        if supplement_thread:
            thinking_html_parts.append(supplement_thread)
        if thinking_html_parts:
            sections.append(self._wrap_meta_section("思考内容", "".join(thinking_html_parts)))
        if enabled_tools:
            sections.append(self._wrap_meta_section("启用工具", self._render_chip_list(enabled_tools)))
        if meta.get("think_level"):
            sections.append(self._wrap_meta_section("思考等级", self._render_chip_list([meta["think_level"]])))
        if meta.get("search_keywords"):
            sections.append(self._wrap_meta_section("搜索关键词", self._render_chip_list(meta["search_keywords"])))
        if meta.get("uris"):
            sections.append(self._wrap_meta_section("搜索来源", self._render_link_list(meta["uris"])))
        if meta.get("ocr_results"):
            ocr_blocks = "".join(self._render_ocr_item(item) for item in meta["ocr_results"])
            sections.append(self._wrap_meta_section("OCR 提取", ocr_blocks))
        if meta.get("tool_call_history"):
            sections.append(self._wrap_meta_section("工具调用", self._render_tool_history(meta["tool_call_history"])))

        if not sections:
            return ""

        return (
            '<details class="meta-box assistant-meta-box" style="margin-bottom: 14px;">'
            f"<summary>{self._render_summary(summary or '查看思考与元数据')}</summary>"
            '<div class="meta-content">'
            f'{"".join(sections)}'
            "</div>"
            "</details>"
        )

    def _render_supplement_thread(
        self,
        assistant_questions: Any,
        user_inputs: Any,
    ) -> str:
        questions = assistant_questions if isinstance(assistant_questions, list) else []
        answers = user_inputs if isinstance(user_inputs, list) else []
        if not questions and not answers:
            return ""

        thread_items: list[str] = []
        total = max(len(questions), len(answers))
        for idx in range(total):
            question_item = questions[idx] if idx < len(questions) else None
            answer_item = answers[idx] if idx < len(answers) else None

            turn_parts: list[str] = []
            if question_item is not None:
                turn_parts.append(self._render_supplement_question(question_item))
            if answer_item not in (None, ""):
                turn_parts.append(
                    '<div class="supplement-user-row">'
                    f'<div class="supplement-user">{_render_markdown_block(str(answer_item))}</div>'
                    "</div>"
                )
            if turn_parts:
                thread_items.append(f'<div class="supplement-turn">{"".join(turn_parts)}</div>')

        if not thread_items:
            return ""
        return f'<div class="supplement-thread">{"".join(thread_items)}</div>'

    def _render_live_assistant_activity(
        self,
        model_name: str,
        meta: dict[str, Any],
        enabled_tools: list[str],
        live_tool_history: list[dict[str, Any]],
        system_messages: list[str],
    ) -> str:
        process_sections: list[str] = []
        merged_tool_history = self._merge_live_tool_history(meta.get("tool_call_history"), live_tool_history)

        if enabled_tools:
            process_sections.append(self._wrap_meta_section("启用工具", self._render_chip_list(enabled_tools)))
        if meta.get("think_level"):
            process_sections.append(self._wrap_meta_section("思考等级", self._render_chip_list([meta["think_level"]])))
        if meta.get("search_keywords"):
            process_sections.append(self._wrap_meta_section("搜索关键词", self._render_chip_list(meta["search_keywords"])))
        if meta.get("uris"):
            process_sections.append(self._wrap_meta_section("搜索来源", self._render_link_list(meta["uris"])))
        if meta.get("ocr_results"):
            ocr_blocks = "".join(self._render_ocr_item(item) for item in meta["ocr_results"])
            process_sections.append(self._wrap_meta_section("OCR 提取", ocr_blocks))
        if merged_tool_history:
            process_sections.append(self._wrap_meta_section("工具调用", self._render_tool_history(merged_tool_history)))
        if system_messages:
            process_sections.append(self._wrap_meta_section("过程日志", _render_markdown_block("\n\n".join(system_messages))))

        if not process_sections:
            return ""

        summary = f"{model_name} 过程元数据" if model_name else "过程元数据"
        return self._render_meta_details_box(summary, "".join(process_sections), extra_class="assistant-process-box live-log")

    def _render_assistant_meta(
        self,
        model_name: str,
        thinking: str,
        meta: dict[str, Any],
        enabled_tools: list[str],
    ) -> str:
        thinking_time = meta.get("thinking_time")
        thinking_sections: list[str] = []
        process_sections: list[str] = []

        supplement_thread = self._render_supplement_thread(
            meta.get("assistant_questions"),
            meta.get("user_inputs"),
        )
        thinking_html_parts: list[str] = []
        if thinking:
            thinking_html_parts.append(_render_markdown_block(thinking))
        if supplement_thread:
            thinking_html_parts.append(supplement_thread)
        if thinking_html_parts:
            thinking_sections.append(self._wrap_meta_section("思考内容", "".join(thinking_html_parts)))

        if enabled_tools:
            process_sections.append(self._wrap_meta_section("启用工具", self._render_chip_list(enabled_tools)))
        if meta.get("think_level"):
            process_sections.append(self._wrap_meta_section("思考等级", self._render_chip_list([meta["think_level"]])))
        if meta.get("search_keywords"):
            process_sections.append(self._wrap_meta_section("搜索关键词", self._render_chip_list(meta["search_keywords"])))
        if meta.get("uris"):
            process_sections.append(self._wrap_meta_section("搜索来源", self._render_link_list(meta["uris"])))
        if meta.get("ocr_results"):
            ocr_blocks = "".join(self._render_ocr_item(item) for item in meta["ocr_results"])
            process_sections.append(self._wrap_meta_section("OCR 提取", ocr_blocks))
        if meta.get("tool_call_history"):
            process_sections.append(self._wrap_meta_section("工具调用", self._render_tool_history(meta["tool_call_history"])))

        blocks: list[str] = []
        if thinking_sections:
            thinking_summary = model_name or ""
            if isinstance(thinking_time, (int, float)) and thinking_time > 0:
                thinking_summary = (
                    f"{thinking_summary} 已思考 {thinking_time:.2f}s"
                    if thinking_summary
                    else f"已思考 {thinking_time:.2f}s"
                )
            blocks.append(
                self._render_meta_details_box(
                    thinking_summary or "查看思考内容",
                    "".join(thinking_sections),
                    extra_class="assistant-thinking-box",
                )
            )
        if process_sections:
            process_summary = f"{model_name} 过程元数据" if model_name else "查看过程元数据"
            blocks.append(
                self._render_meta_details_box(
                    process_summary,
                    "".join(process_sections),
                    extra_class="assistant-process-box",
                )
            )

        return "".join(blocks)

    def _render_supplement_question(self, question_item: Any) -> str:
        if isinstance(question_item, dict):
            question_text = str(question_item.get("question", "") or "")
            input_type = str(question_item.get("type", "") or "")
            missing_param = str(question_item.get("missing_param", "") or "")
            options = question_item.get("options", [])

            meta_bits = []
            if input_type:
                meta_bits.append(f"需要你{html.escape(input_type)}")
            if missing_param:
                meta_bits.append(f"补充项：{html.escape(missing_param)}")
            meta_html = ""
            if meta_bits:
                meta_html += f'<div class="supplement-meta">{" · ".join(meta_bits)}</div>'
            if isinstance(options, list) and options:
                chips = "".join(f'<span class="chip">{html.escape(str(option))}</span>' for option in options)
                meta_html += f'<div class="chip-list" style="margin-top: 8px;">{chips}</div>'

            return (
                '<div class="supplement-assistant">'
                f'{_render_markdown_block(question_text)}'
                f"{meta_html}"
                "</div>"
            )

        return f'<div class="supplement-assistant">{_render_markdown_block(str(question_item))}</div>'

    def _render_ocr_item(self, item: dict[str, Any]) -> str:
        image_path = str(item.get("image_path", "") or "")
        ocr_text = str(item.get("ocr_text", "") or "")
        extra = ""
        if image_path:
            file_url = self._browser_file_url(image_path)
            extra = (
                '<div style="margin-bottom: 10px;">'
                f'<a href="{file_url}" target="_blank" rel="noreferrer">{html.escape(os.path.basename(image_path))}</a>'
                "</div>"
            )
        return f'<div class="kv-item">{extra}{_render_markdown_block(ocr_text)}</div>'

    def _render_tool_history(self, content: Any) -> str:
        items = content if isinstance(content, list) else []
        if not items:
            return self._render_data_block(content)

        blocks = []
        for item in items:
            if not isinstance(item, dict):
                continue
            detail_blocks = []
            for key, value in item.items():
                if key == "name":
                    continue
                detail_blocks.append(
                    f'<div class="kv-item"><div class="kv-key">{html.escape(str(key))}</div>{self._render_data_block(value)}</div>'
                )
            detail_html = f'<div class="kv-list">{"".join(detail_blocks)}</div>' if detail_blocks else ""
            blocks.append(
                '<div class="tool-item">'
                f'<div><span class="tool-name">{html.escape(str(item.get("name", "tool")))}</span>'
                f'<span class="tool-status">{html.escape(str(item.get("status", "")))}</span></div>'
                f"{detail_html}"
                "</div>"
            )
        return f'<div class="tool-list">{"".join(blocks)}</div>'

    def _render_link_list(self, links: list[Any]) -> str:
        items = []
        for link in links:
            raw = str(link).strip()
            title = raw
            href = raw
            match = re.match(r"^-?\s*\[([^\]]+)\]\(([^)]+)\)\s*$", raw)
            if match:
                title = match.group(1).strip() or match.group(2).strip()
                href = match.group(2).strip()
            items.append(
                '<div class="source-item">'
                f'<a class="source-title" href="{html.escape(href, quote=True)}" target="_blank" rel="noreferrer">{html.escape(title)}</a>'
                f'<div class="source-url">{html.escape(raw)}</div>'
                "</div>"
            )
        return f'<div class="source-list">{"".join(items)}</div>'

    def _render_chip_list(self, values: list[Any]) -> str:
        chips = "".join(f'<span class="chip">{html.escape(str(value))}</span>' for value in values if value not in (None, ""))
        return f'<div class="chip-list">{chips}</div>'

    def _render_list_block(self, values: list[Any]) -> str:
        items = "".join(f'<div class="kv-item">{self._render_data_block(value)}</div>' for value in values)
        return f'<div class="kv-list">{"".join(items)}</div>'

    def _render_data_block(self, value: Any) -> str:
        if isinstance(value, dict):
            parts = []
            for key, inner_value in value.items():
                parts.append(
                    f'<div class="kv-item"><div class="kv-key">{html.escape(str(key))}</div>{self._render_data_block(inner_value)}</div>'
                )
            return f'<div class="kv-list">{"".join(parts)}</div>'
        if isinstance(value, list):
            return self._render_list_block(value)
        return _render_markdown_block("" if value is None else str(value))

    def _wrap_meta_section(self, title: str, body: str) -> str:
        return f'<section class="meta-section"><div class="meta-title">{html.escape(title)}</div>{body}</section>'

    def _render_summary(self, text: str) -> str:
        return (
            '<div class="summary-row">'
            f'<span class="summary-label">{html.escape(text)}</span>'
            '<span class="summary-caret" aria-hidden="true"></span>'
            "</div>"
        )

    def _render_meta_details_box(self, summary: str, body: str, extra_class: str = "") -> str:
        class_name = "meta-box assistant-meta-box"
        if extra_class:
            class_name += f" {extra_class.strip()}"
        return (
            f'<details class="{class_name}" style="margin-bottom: 14px;">'
            f"<summary>{self._render_summary(summary)}</summary>"
            '<div class="meta-content">'
            f"{body}"
            "</div>"
            "</details>"
        )

    def _browser_file_url(self, path: str) -> str:
        return f"/api/file?path={quote(os.path.abspath(path))}"

    def _handle_file_request(self, handler: BaseHTTPRequestHandler, parsed) -> None:
        query = parse_qs(parsed.query)
        raw_path = query.get("path", [""])[0]
        if not raw_path:
            self._send_json(handler, {"error": "缺少 path"}, status=400)
            return

        abs_path = os.path.abspath(raw_path)
        real_path = os.path.realpath(abs_path)
        if not real_path.startswith(os.path.realpath(self.project_root)):
            self._send_json(handler, {"error": "禁止访问该文件"}, status=403)
            return
        if not os.path.exists(real_path) or not os.path.isfile(real_path):
            self._send_json(handler, {"error": "文件不存在"}, status=404)
            return

        mime_type, _ = mimetypes.guess_type(real_path)
        mime_type = mime_type or "application/octet-stream"
        with open(real_path, "rb") as handle:
            data = handle.read()

        handler.send_response(200)
        handler.send_header("Content-Type", mime_type)
        handler.send_header("Content-Length", str(len(data)))
        handler.end_headers()
        handler.wfile.write(data)

    def _read_json_body(self, handler: BaseHTTPRequestHandler) -> dict[str, Any]:
        content_length = int(handler.headers.get("Content-Length", "0") or 0)
        raw_body = handler.rfile.read(content_length) if content_length > 0 else b"{}"
        if not raw_body:
            return {}
        try:
            return json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def _send_html(self, handler: BaseHTTPRequestHandler, body: str, status: int = 200) -> None:
        data = body.encode("utf-8")
        handler.send_response(status)
        handler.send_header("Content-Type", "text/html; charset=utf-8")
        handler.send_header("Content-Length", str(len(data)))
        handler.end_headers()
        handler.wfile.write(data)

    def _send_json(self, handler: BaseHTTPRequestHandler, payload: dict[str, Any], status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(data)))
        handler.end_headers()
        handler.wfile.write(data)

    def _build_model_catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "deepseek",
                "label": "DeepSeek",
                "supports_attachments": True,
                "thinking": {
                    "default": "reasoner",
                    "options": [
                        {"value": "reasoner", "label": "深度"},
                        {"value": "chat", "label": "快速"},
                    ],
                },
                "extra_fields": [
                    {"key": "enable_search", "type": "boolean", "label": "联网搜索", "default": False},
                    {
                        "key": "search_effort",
                        "type": "select",
                        "label": "搜索强度",
                        "default": "low",
                        "show_when": {"key": "enable_search", "equals": True},
                        "options": [
                            {"value": "time_only", "label": "仅时间"},
                            {"value": "minimal", "label": "极低"},
                            {"value": "low", "label": "低"},
                            {"value": "medium", "label": "中"},
                            {"value": "high", "label": "高"},
                            {"value": "max", "label": "最大"},
                            {"value": "unlimited", "label": "无限制"},
                        ],
                    },
                    {"key": "interactive_thinking", "type": "boolean", "label": "交互式思考", "default": False},
                ],
            },
            {
                "id": "deepseek-agent-preview",
                "label": "DeepSeek Agent",
                "supports_attachments": True,
                "thinking": None,
                "extra_fields": [
                    {"key": "enable_search", "type": "boolean", "label": "联网搜索", "default": True},
                    {
                        "key": "search_effort",
                        "type": "select",
                        "label": "搜索强度",
                        "default": "medium",
                        "show_when": {"key": "enable_search", "equals": True},
                        "options": [
                            {"value": "minimal", "label": "极低"},
                            {"value": "low", "label": "低"},
                            {"value": "medium", "label": "中"},
                            {"value": "high", "label": "高"},
                            {"value": "max", "label": "最大"},
                            {"value": "unlimited", "label": "无限制"},
                        ],
                    },
                    {"key": "interactive_thinking", "type": "boolean", "label": "交互式思考", "default": False},
                ],
            },
            {
                "id": "gemini-3.1-flash-lite-preview",
                "label": "Gemini 3.1 Flash Lite",
                "supports_attachments": True,
                "thinking": self._level_options(default="medium"),
                "extra_fields": [{"key": "enable_search", "type": "boolean", "label": "Google 搜索", "default": False}],
            },
            {
                "id": "gemini-3-flash-preview",
                "label": "Gemini 3 Flash",
                "supports_attachments": True,
                "thinking": self._level_options(default="medium"),
                "extra_fields": [{"key": "enable_search", "type": "boolean", "label": "Google 搜索", "default": False}],
            },
            {
                "id": "gemini-3.1-pro-preview",
                "label": "Gemini 3.1 Pro",
                "supports_attachments": True,
                "thinking": self._level_options(default="medium"),
                "extra_fields": [{"key": "enable_search", "type": "boolean", "label": "Google 搜索", "default": False}],
            },
            {
                "id": "qwen3.5-plus",
                "label": "Qwen 3.5 Plus",
                "supports_attachments": True,
                "thinking": {
                    "default": "auto",
                    "options": [
                        {"value": "auto", "label": "自动"},
                        {"value": "enabled", "label": "开启"},
                        {"value": "disabled", "label": "关闭"},
                    ],
                },
                "extra_fields": [
                    {"key": "enable_search", "type": "boolean", "label": "联网搜索", "default": False},
                    {
                        "key": "search_strategy",
                        "type": "select",
                        "label": "搜索策略",
                        "default": "turbo",
                        "show_when": {"key": "enable_search", "equals": True},
                        "options": [
                            {"value": "turbo", "label": "Turbo"},
                            {"value": "max", "label": "Max"},
                            {"value": "agent", "label": "Agent"},
                            {"value": "agent_max", "label": "Agent Max"},
                        ],
                    },
                ],
            },
            {
                "id": "qwen3.6-plus",
                "label": "Qwen 3.6 Plus",
                "supports_attachments": True,
                "thinking": {
                    "default": "auto",
                    "options": [
                        {"value": "auto", "label": "自动"},
                        {"value": "enabled", "label": "开启"},
                        {"value": "disabled", "label": "关闭"},
                    ],
                },
                "extra_fields": [
                    {"key": "enable_search", "type": "boolean", "label": "联网搜索", "default": False},
                    {
                        "key": "search_strategy",
                        "type": "select",
                        "label": "搜索策略",
                        "default": "turbo",
                        "show_when": {"key": "enable_search", "equals": True},
                        "options": [
                            {"value": "turbo", "label": "Turbo"},
                            {"value": "max", "label": "Max"},
                            {"value": "agent", "label": "Agent"},
                            {"value": "agent_max", "label": "Agent Max"},
                        ],
                    },
                ],
            },
            {
                "id": "doubao-seed-2-0-pro-260215",
                "label": "Doubao Pro",
                "supports_attachments": True,
                "thinking": self._level_options(default="medium"),
                "extra_fields": [{"key": "enable_search", "type": "boolean", "label": "联网搜索", "default": False}],
            },
            {
                "id": "doubao-seed-2-0-lite-260215",
                "label": "Doubao Lite",
                "supports_attachments": True,
                "thinking": self._level_options(default="medium"),
                "extra_fields": [{"key": "enable_search", "type": "boolean", "label": "联网搜索", "default": False}],
            },
            {
                "id": "doubao-seed-2-0-mini-260215",
                "label": "Doubao Mini",
                "supports_attachments": True,
                "thinking": self._level_options(default="medium"),
                "extra_fields": [{"key": "enable_search", "type": "boolean", "label": "联网搜索", "default": False}],
            },
            {
                "id": "kimi-k2.5",
                "label": "Kimi K2.5",
                "supports_attachments": True,
                "thinking": {
                    "default": "enabled",
                    "options": [
                        {"value": "enabled", "label": "开启"},
                        {"value": "disabled", "label": "关闭"},
                    ],
                },
                "extra_fields": [{"key": "enable_search", "type": "boolean", "label": "联网搜索", "default": False}],
            },
            {
                "id": "MiniMax-M2.7",
                "label": "MiniMax M2.7",
                "supports_attachments": True,
                "thinking": None,
                "extra_fields": [{"key": "enable_search", "type": "boolean", "label": "联网搜索", "default": False}],
            },
            {
                "id": "MiniMax-M2.5",
                "label": "MiniMax M2.5",
                "supports_attachments": True,
                "thinking": None,
                "extra_fields": [{"key": "enable_search", "type": "boolean", "label": "联网搜索", "default": False}],
            },
            {
                "id": "multi-assistant-old-preview",
                "label": "Multi Assistant",
                "supports_attachments": True,
                "thinking": None,
                "extra_fields": [],
            },
        ]

    def _level_options(self, default: str) -> dict[str, Any]:
        return {
            "default": default,
            "options": [
                {"value": "minimal", "label": "极低"},
                {"value": "low", "label": "低"},
                {"value": "medium", "label": "中"},
                {"value": "high", "label": "高"},
            ],
        }

    def _model_exists(self, model_id: str) -> bool:
        return any(item["id"] == model_id for item in self.model_catalog)

    def _theme_exists(self, theme_id: str) -> bool:
        return any(item["id"] == theme_id for item in self.THEME_OPTIONS)

    def _accent_exists(self, accent_id: str) -> bool:
        return any(item["id"] == accent_id for item in self.ACCENT_OPTIONS)

    def _resolve_browser_accent(self, theme_id: str, raw_accent: Any) -> str:
        accent_id = str(raw_accent or "").strip().lower()
        if self._accent_exists(accent_id):
            return accent_id
        if theme_id == "black":
            return "blue"
        return theme_id if self._accent_exists(theme_id) else "orange"
