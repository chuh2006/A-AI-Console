import ast
import base64
import html
import mimetypes
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from latex2mathml.converter import convert as latex_to_mathml


def render_chat_archive_html(full_context: list[dict], title: str) -> str:
    structure = _build_render_structure(full_context)
    turns_html = "\n".join(_render_turn(turn) for turn in structure["turns"])
    title_html = html.escape(title)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title_html}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
    <style>
        :root {{
            --bg: #ffffff;
            --text: #222222;
            --muted: #7a756c;
            --line: #e6e0d6;
            --accent: #d97757;
            --user: #ece9e4;
            --code-bg: #1f1f1f;
            --code-text: #f3f3f3;
            --shadow: 0 10px 30px rgba(51, 41, 28, 0.08);
            --meta-summary: #847c70;
            --meta-text: #6d665c;
        }}
        * {{
            box-sizing: border-box;
        }}
        body {{
            margin: 0;
            background: var(--bg);
            color: var(--text);
            font-family: "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif;
            line-height: 1.72;
        }}
        .page {{
            max-width: 980px;
            margin: 0 auto;
            padding: 36px 24px 64px;
        }}
        .header {{
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 28px;
        }}
        .header-main {{
            min-width: 0;
        }}
        .title {{
            margin: 0;
            font-size: 28px;
            font-weight: 700;
            letter-spacing: 0.01em;
        }}
        .header-actions {{
            flex: 0 0 auto;
        }}
        .toggle-all-button {{
            padding: 10px 14px;
            border: 1px solid var(--line);
            border-radius: 999px;
            background: #ffffff;
            color: var(--muted);
            font: inherit;
            font-size: 14px;
            cursor: pointer;
            box-shadow: var(--shadow);
            transition: border-color 0.18s ease, color 0.18s ease, transform 0.18s ease;
        }}
        .toggle-all-button:hover {{
            color: var(--text);
            border-color: #d8d0c4;
            transform: translateY(-1px);
        }}
        .toggle-all-button:active {{
            transform: translateY(0);
        }}
        .system-panel {{
            margin-bottom: 28px;
        }}
        details.meta-box {{
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 18px;
            box-shadow: var(--shadow);
            overflow: hidden;
        }}
        details.meta-box summary {{
            cursor: pointer;
            list-style: none;
            font-size: 14px;
            color: var(--muted);
            user-select: none;
            padding: 0;
        }}
        details.meta-box summary::-webkit-details-marker {{
            display: none;
        }}
        details.meta-box[open] summary {{
            border-bottom: 1px solid var(--line);
            color: var(--text);
        }}
        .meta-content {{
            padding: 16px 18px 18px;
            background: #ffffff;
        }}
        .summary-row {{
            display: inline-flex;
            align-items: center;
            justify-content: flex-start;
            gap: 10px;
            max-width: 100%;
            padding: 12px 16px;
        }}
        .summary-label {{
            min-width: 0;
            overflow-wrap: anywhere;
        }}
        .summary-caret {{
            flex: 0 0 auto;
            width: 0;
            height: 0;
            border-top: 5px solid transparent;
            border-bottom: 5px solid transparent;
            border-left: 7px solid currentColor;
            color: var(--muted);
            transform-origin: 35% 50%;
            transition: transform 0.18s ease;
        }}
        details.meta-box[open] .summary-caret {{
            transform: rotate(90deg);
        }}
        details.assistant-meta-box {{
            display: inline-block;
            width: auto;
            max-width: 100%;
            vertical-align: top;
        }}
        details.assistant-meta-box[open] {{
            width: min(100%, 760px);
        }}
        details.assistant-meta-box summary {{
            color: var(--meta-summary);
        }}
        details.assistant-meta-box[open] summary {{
            color: var(--meta-summary);
        }}
        details.assistant-meta-box .meta-content,
        details.assistant-meta-box .message-content {{
            color: var(--meta-text);
        }}
        .assistant-meta-inline {{
            display: inline-flex;
            align-items: center;
            justify-content: flex-start;
            gap: 10px;
            margin-bottom: 14px;
            padding: 12px 16px;
            border: 1px solid var(--line);
            border-radius: 18px;
            background: #ffffff;
            box-shadow: var(--shadow);
            color: var(--muted);
            font-size: 14px;
            max-width: 100%;
        }}
        .turn {{
            margin-bottom: 28px;
        }}
        .turn-index {{
            margin-bottom: 8px;
            color: var(--muted);
            font-size: 13px;
        }}
        .user-row {{
            display: flex;
            justify-content: flex-end;
        }}
        .user-bubble {{
            max-width: min(82%, 720px);
            background: var(--user);
            border-radius: 22px;
            padding: 16px 18px;
            box-shadow: var(--shadow);
        }}
        .assistant-block {{
            margin-top: 14px;
            padding-left: 6px;
        }}
        .message-content {{
            font-size: 16px;
            overflow-wrap: anywhere;
        }}
        .message-content > :first-child {{
            margin-top: 0;
        }}
        .message-content > :last-child {{
            margin-bottom: 0;
        }}
        .message-content h1,
        .message-content h2,
        .message-content h3,
        .message-content h4 {{
            margin: 1.1em 0 0.55em;
            line-height: 1.35;
        }}
        .message-content h1 {{
            font-size: 1.42em;
        }}
        .message-content h2 {{
            font-size: 1.25em;
        }}
        .message-content h3 {{
            font-size: 1.12em;
        }}
        .message-content p,
        .message-content ul,
        .message-content ol,
        .message-content blockquote,
        .message-content pre {{
            margin: 0 0 0.9em;
        }}
        .message-content hr {{
            margin: 1.05em 0;
            border: 0;
            border-top: 1px solid var(--line);
        }}
        .message-content ul,
        .message-content ol {{
            padding-left: 1.4em;
        }}
        .message-content li + li {{
            margin-top: 0.25em;
        }}
        .message-content blockquote {{
            margin-left: 0;
            padding: 0.1em 1em;
            border-left: 3px solid #d7c9ba;
            color: #5f5a52;
            background: rgba(255, 255, 255, 0.72);
            border-radius: 0 12px 12px 0;
        }}
        .message-content code {{
            padding: 0.1em 0.36em;
            border-radius: 6px;
            background: #efe7db;
            font-family: "Cascadia Code", "Consolas", monospace;
            font-size: 0.92em;
        }}
        .message-content pre {{
            padding: 14px 16px;
            border-radius: 14px;
            background: var(--code-bg);
            color: var(--code-text);
            overflow-x: auto;
            box-shadow: inset 0 0 0 1px rgba(255,255,255,0.05);
        }}
        .message-content pre code {{
            padding: 0;
            background: transparent;
            color: inherit;
        }}
        .message-content table {{
            width: 100%;
            border-collapse: collapse;
            margin: 0 0 0.95em;
            display: block;
            overflow-x: auto;
            border: 1px solid var(--line);
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.88);
        }}
        .message-content th,
        .message-content td {{
            border: 1px solid var(--line);
            padding: 8px 10px;
            min-width: 88px;
            vertical-align: top;
        }}
        .message-content th {{
            background: #f6efe5;
            font-weight: 700;
        }}
        .message-content tr:nth-child(even) td {{
            background: rgba(255, 255, 255, 0.55);
        }}
        .message-content .katex-display,
        .message-content .math-block {{
            overflow-x: auto;
            overflow-y: hidden;
            padding: 0.15em 0;
        }}
        .message-content a {{
            color: #0f5ec9;
            text-decoration: none;
        }}
        .message-content .math-inline {{
            display: inline-flex;
            max-width: 100%;
            overflow-x: auto;
            overflow-y: hidden;
            vertical-align: middle;
        }}
        .message-content .math-block {{
            display: block;
            width: 100%;
            margin: 1em 0;
            text-align: center;
        }}
        .message-content .math-inline math,
        .message-content .math-block math {{
            font-size: 1em;
        }}
        .message-content .math-block math {{
            display: inline-block;
        }}
        .message-content a:hover {{
            text-decoration: underline;
        }}
        .image-grid {{
            display: grid;
            gap: 12px;
            margin-top: 12px;
        }}
        .image-card {{
            background: rgba(255,255,255,0.82);
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 10px;
            overflow: hidden;
        }}
        .message-content img {{
            display: block;
            width: auto;
            max-width: 100%;
            height: auto;
            max-height: min(56vh, 460px);
            object-fit: contain;
            border-radius: 10px;
            background: #fff;
        }}
        .image-card img {{
            display: block;
            width: 100%;
            max-width: 100%;
            height: auto;
            border-radius: 10px;
            max-height: min(56vh, 420px);
            object-fit: contain;
            background: #fff;
        }}
        .meta-section + .meta-section {{
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid var(--line);
        }}
        .meta-title {{
            margin-bottom: 8px;
            font-size: 13px;
            font-weight: 700;
            color: var(--muted);
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }}
        .chip-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}
        .chip {{
            display: inline-flex;
            align-items: center;
            padding: 6px 10px;
            border-radius: 999px;
            background: #efe7db;
            color: #5a4632;
            font-size: 13px;
        }}
        .tool-list {{
            display: grid;
            gap: 10px;
        }}
        .tool-item {{
            padding: 12px 14px;
            border: 1px solid var(--line);
            border-radius: 14px;
            background: rgba(255,255,255,0.9);
        }}
        .tool-name {{
            font-weight: 600;
        }}
        .tool-status {{
            margin-left: 8px;
            color: var(--accent);
            font-size: 13px;
        }}
        .kv-list {{
            display: grid;
            gap: 8px;
        }}
        .kv-item {{
            padding: 10px 12px;
            border-radius: 12px;
            background: rgba(255,255,255,0.9);
            border: 1px solid var(--line);
        }}
        .kv-key {{
            font-size: 12px;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 4px;
        }}
        .source-list {{
            display: grid;
            gap: 10px;
        }}
        .source-item {{
            padding: 12px 14px;
            border-radius: 14px;
            background: rgba(255,255,255,0.9);
            border: 1px solid var(--line);
        }}
        .source-title {{
            color: #0f5ec9;
            font-weight: 600;
            text-decoration: none;
        }}
        .source-title:hover {{
            text-decoration: underline;
        }}
        .source-url {{
            margin-top: 4px;
            color: var(--muted);
            font-size: 12px;
            overflow-wrap: anywhere;
        }}
        @media (max-width: 720px) {{
            .page {{
                padding: 22px 14px 42px;
            }}
            .header {{
                flex-direction: column;
                align-items: stretch;
            }}
            .title {{
                font-size: 24px;
            }}
            .user-bubble {{
                max-width: 100%;
            }}
            .message-content img,
            .image-card img {{
                max-height: 46vh;
            }}
        }}
    </style>
</head>
<body>
    <main class="page">
        <header class="header">
            <div class="header-main">
                <h1 class="title">{title_html}</h1>
            </div>
            <div class="header-actions">
                <button class="toggle-all-button" type="button" id="toggle-all-details">全部展开</button>
            </div>
        </header>
        <section class="conversation">
            {turns_html}
        </section>
    </main>
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
    <script>
        (() => {{
            const detailsList = Array.from(document.querySelectorAll('details.meta-box'));
            const toggleButton = document.getElementById('toggle-all-details');
            if (!toggleButton || detailsList.length === 0) {{
                if (toggleButton) {{
                    toggleButton.style.display = 'none';
                }}
                return;
            }}

            const syncButtonLabel = () => {{
                const allOpen = detailsList.every((item) => item.open);
                toggleButton.textContent = allOpen ? '全部折叠' : '全部展开';
            }};

            toggleButton.addEventListener('click', () => {{
                const shouldOpenAll = detailsList.some((item) => !item.open);
                detailsList.forEach((item) => {{
                    item.open = shouldOpenAll;
                }});
                syncButtonLabel();
            }});

            detailsList.forEach((item) => {{
                item.addEventListener('toggle', syncButtonLabel);
            }});

            syncButtonLabel();

            if (typeof window.renderMathInElement === 'function') {{
                const mathRoot = document.querySelector('.page');
                if (mathRoot) {{
                    window.renderMathInElement(mathRoot, {{
                    delimiters: [
                        {{ left: '$$', right: '$$', display: true }},
                        {{ left: '\\[', right: '\\]', display: true }},
                        {{ left: '\\(', right: '\\)', display: false }},
                        {{ left: '$', right: '$', display: false }},
                    ],
                    throwOnError: false,
                    strict: 'ignore',
                    ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'],
                    }});
                }}
            }}
        }})();
    </script>
</body>
</html>
"""


def _build_render_structure(full_context: list[dict]) -> dict:
    turns = []
    system_messages = []
    misc_messages = []
    current_turn = None
    pending_epoch = None
    pending_user_meta = []
    pending_process_items: list[dict] = []

    def ensure_turn() -> dict:
        nonlocal current_turn
        if current_turn is None:
            current_turn = {
                "epoch": pending_epoch,
                "user": None,
                "user_meta": [],
                "assistant_model": "",
                "assistant_blocks": [],
            }
        return current_turn

    def get_last_thinking_block() -> dict | None:
        turn = ensure_turn()
        for block in reversed(turn["assistant_blocks"]):
            if block.get("kind") == "thinking":
                return block
        return None

    def flush_pending_process() -> None:
        if not pending_process_items:
            return
        payload = _build_legacy_process_payload(pending_process_items)
        pending_process_items.clear()
        if payload:
            ensure_turn()["assistant_blocks"].append({"kind": "process", "content": payload})

    def flush_turn() -> None:
        nonlocal current_turn, pending_epoch, pending_user_meta
        flush_pending_process()
        if current_turn and (
            current_turn["user"] is not None
            or current_turn["user_meta"]
            or current_turn["assistant_blocks"]
        ):
            turns.append(current_turn)
        current_turn = None
        pending_epoch = None
        pending_user_meta = []

    for msg in full_context:
        if not isinstance(msg, dict):
            continue

        role = msg.get("role")
        content = msg.get("content")

        if role == "directions":
            misc_messages.append(msg)
            continue

        if role == "system":
            system_messages.append(msg)
            continue

        if role == "epoch_count":
            if current_turn and (current_turn["user"] is not None or current_turn["assistant_blocks"]):
                flush_turn()
            pending_epoch = content
            continue

        if role in {"image_uploaded", "user_original"}:
            pending_user_meta.append(msg)
            continue

        if role == "user":
            if current_turn and (current_turn["user"] is not None or current_turn["assistant_blocks"]):
                flush_turn()
            current_turn = {
                "epoch": pending_epoch,
                "user": content,
                "user_meta": pending_user_meta.copy(),
                "assistant_model": "",
                "assistant_blocks": [],
            }
            pending_user_meta = []
            continue

        if role == "model":
            ensure_turn()["assistant_model"] = str(content or "").strip()
            continue

        if role == "assistant_thinking":
            flush_pending_process()
            block = {"kind": "thinking", "content": str(content or "")}
            thinking_time = _coerce_numeric_time(msg.get("thinking_time"))
            if thinking_time is not None and thinking_time > 0:
                block["thinking_time"] = thinking_time
            assistant_questions = msg.get("assistant_questions")
            if isinstance(assistant_questions, list) and assistant_questions:
                block["assistant_questions"] = list(assistant_questions)
            user_inputs = msg.get("user_inputs")
            if isinstance(user_inputs, list) and user_inputs:
                block["user_inputs"] = list(user_inputs)
            ensure_turn()["assistant_blocks"].append(block)
            continue

        if role == "assistant_thinking_time":
            last_thinking = get_last_thinking_block()
            if last_thinking is not None:
                thinking_time = _coerce_numeric_time(content)
                if thinking_time is not None and thinking_time > 0:
                    last_thinking["thinking_time"] = thinking_time
            continue

        if role == "assistant_questions":
            last_thinking = get_last_thinking_block()
            if last_thinking is not None:
                last_thinking.setdefault("assistant_questions", [])
                last_thinking["assistant_questions"].extend(_coerce_list(content))
            else:
                pending_process_items.append(msg)
            continue

        if role == "user_inputs":
            last_thinking = get_last_thinking_block()
            if last_thinking is not None:
                last_thinking.setdefault("user_inputs", [])
                last_thinking["user_inputs"].extend(_coerce_list(content))
            else:
                pending_process_items.append(msg)
            continue

        if role == "assistant_process":
            flush_pending_process()
            if isinstance(content, dict):
                ensure_turn()["assistant_blocks"].append({"kind": "process", "content": dict(content)})
            elif content not in (None, ""):
                ensure_turn()["assistant_blocks"].append({"kind": "process", "content": {"raw": content}})
            continue

        if role in {"assistant_answer", "assistant_tool_calls"}:
            flush_pending_process()
            ensure_turn()["assistant_blocks"].append({"kind": "answer", "content": str(content or "")})
            continue

        if role == "tool":
            continue

        if role in {
            "search_results_links",
            "thinking_level",
            "tool_ocr_extraction",
            "search_keywords",
            "tool_call_history",
            "assistant_original_answer",
            "enabled_tools",
        }:
            pending_process_items.append(msg)
            continue

        misc_messages.append(msg)

    if pending_user_meta:
        ensure_turn()["user_meta"].extend(pending_user_meta)

    flush_turn()

    return {
        "turns": turns,
        "system_messages": system_messages,
        "misc_messages": misc_messages,
    }


def _render_system_panel(system_messages: list[dict], misc_messages: list[dict]) -> str:
    sections = []
    if system_messages:
        rendered = "".join(
            f'<div class="meta-section"><div class="meta-title">系统提示</div>{_render_markdown_block(str(msg.get("content", "")))}</div>'
            for msg in system_messages
        )
        sections.append(rendered)

    extra_items = [msg for msg in misc_messages if msg.get("role") != "directions"]
    if extra_items:
        rendered_items = "".join(
            f'<div class="meta-section"><div class="meta-title">{html.escape(str(msg.get("role", "")))}</div>{_render_data_block(msg.get("content", ""))}</div>'
            for msg in extra_items
        )
        sections.append(rendered_items)

    if not sections:
        return ""

    body = "".join(sections)
    return f"""
<section class="system-panel">
    <details class="meta-box">
        <summary>{_render_summary_content("查看系统设定与附加记录")}</summary>
        <div class="meta-content">
            {body}
        </div>
    </details>
</section>
"""


def _render_turn(turn: dict) -> str:
    epoch_label = ""
    if turn.get("epoch") not in (None, ""):
        epoch_label = f'<div class="turn-index">第 {html.escape(str(turn["epoch"]))} 轮</div>'

    user_html = ""
    if turn.get("user") is not None:
        extras = "".join(_render_user_meta(item) for item in turn.get("user_meta", []))
        user_html = f"""
<div class="user-row">
    <div class="user-bubble">
        {_render_markdown_block(str(turn["user"]))}
        {extras}
    </div>
</div>
"""

    assistant_blocks_html = _render_assistant_blocks(
        turn.get("assistant_blocks", []),
        turn.get("assistant_model", ""),
    )

    return f"""
<article class="turn">
    {epoch_label}
    {user_html}
    <div class="assistant-block">
        {assistant_blocks_html}
    </div>
</article>
"""


def _wrap_meta_section(title: str, body: str) -> str:
    return f'<section class="meta-section"><div class="meta-title">{html.escape(title)}</div>{body}</section>'


def _render_summary_content(text: str) -> str:
    return (
        '<div class="summary-row">'
        f'<span class="summary-label">{html.escape(text)}</span>'
        '<span class="summary-caret" aria-hidden="true"></span>'
        '</div>'
    )


def _build_assistant_summary(model_name: str, thinking_time: str) -> str:
    if model_name and thinking_time:
        return f"{model_name} 已思考 {thinking_time}"
    if model_name:
        return model_name
    if thinking_time:
        return f"已思考 {thinking_time}"
    return "查看思考与元数据"


def _render_user_meta(item: dict) -> str:
    role = item.get("role")
    content = item.get("content")

    if role == "image_uploaded":
        image_paths = _coerce_list(content)
        if not image_paths:
            return ""
        cards = []
        for path in image_paths:
            path_str = str(path)
            uri = _normalize_image_src(path_str)
            cards.append(f'<div class="image-card"><img src="{uri}" alt="用户上传图片"></div>')
        return f'<div class="image-grid">{"".join(cards)}</div>'

    if role == "user_original":
        return f"""
<details class="meta-box" style="margin-top: 12px;">
    <summary>{_render_summary_content("查看原始用户输入")}</summary>
    <div class="meta-content">{_render_markdown_block(str(content))}</div>
</details>
"""

    return ""


def _render_assistant_blocks(blocks: list[dict], model_name: str = "") -> str:
    if not blocks:
        return ""
    return "".join(_render_assistant_block(block, model_name) for block in blocks)


def _render_assistant_block(block: dict, model_name: str = "") -> str:
    if not isinstance(block, dict):
        return ""

    kind = str(block.get("kind", "")).strip().lower()
    if kind == "thinking":
        return _render_assistant_thinking_block(block, model_name)
    if kind == "process":
        return _render_assistant_process_block(block, model_name)
    if kind == "answer":
        return f'<div class="assistant-answer">{_render_markdown_block(str(block.get("content", "")))}</div>'
    return ""


def _render_assistant_thinking_block(block: dict, model_name: str = "") -> str:
    sections = []
    thinking_content = str(block.get("content", ""))
    assistant_questions = block.get("assistant_questions")
    user_inputs = block.get("user_inputs")
    thinking_time = _format_thinking_time(_coerce_numeric_time(block.get("thinking_time")))

    if thinking_content:
        sections.append(_wrap_meta_section("思考内容", _render_markdown_block(thinking_content)))
    if assistant_questions:
        sections.append(_wrap_meta_section("追问列表", _render_list_block(assistant_questions)))
    if user_inputs:
        sections.append(_wrap_meta_section("用户补充", _render_list_block(user_inputs)))

    summary = _build_assistant_summary(model_name, thinking_time)
    if not sections:
        return f'<div class="assistant-meta-inline">{html.escape(summary)}</div>' if summary else ""

    return f"""
<details class="meta-box assistant-meta-box assistant-thinking-box" style="margin-bottom: 14px;">
    <summary>{_render_summary_content(summary or "查看思考内容")}</summary>
    <div class="meta-content">
        {"".join(sections)}
    </div>
</details>
"""


def _render_assistant_process_block(block: dict, model_name: str = "") -> str:
    payload = block.get("content", {})
    if not isinstance(payload, dict):
        payload = {"raw": payload}

    sections = []
    enabled_tools = payload.get("enabled_tools")
    if enabled_tools:
        sections.append(_wrap_meta_section("启用工具", _render_chip_list(enabled_tools)))

    think_level = payload.get("think_level")
    if think_level not in (None, ""):
        sections.append(_wrap_meta_section("思考等级", _render_chip_list([think_level])))

    search_keywords = payload.get("search_keywords")
    if search_keywords:
        sections.append(_wrap_meta_section("搜索关键词", _render_chip_list(search_keywords)))

    uris = payload.get("uris")
    if uris:
        sections.append(_wrap_meta_section("搜索来源", _render_link_list(uris)))

    ocr_results = payload.get("ocr_results")
    if ocr_results:
        ocr_blocks = "".join(_render_ocr_result(item) for item in ocr_results)
        sections.append(_wrap_meta_section("OCR 提取", ocr_blocks))

    tool_call_history = payload.get("tool_call_history")
    if tool_call_history:
        sections.append(_wrap_meta_section("工具调用", _render_tool_history(tool_call_history)))

    system_messages = payload.get("system_messages")
    if system_messages:
        sections.append(_wrap_meta_section("过程日志", _render_markdown_block("\n\n".join(_coerce_list(system_messages)))))

    original_answer = payload.get("assistant_original_answer")
    if original_answer not in (None, ""):
        sections.append(_wrap_meta_section("原始回答", _render_markdown_block(str(original_answer))))

    raw_content = payload.get("raw")
    if raw_content not in (None, ""):
        sections.append(_wrap_meta_section("过程元数据", _render_data_block(raw_content)))

    if not sections:
        return ""

    process_summary = f"{model_name} 过程元数据" if model_name else "查看过程元数据"
    return f"""
<details class="meta-box assistant-meta-box assistant-process-box" style="margin-bottom: 14px;">
    <summary>{_render_summary_content(process_summary)}</summary>
    <div class="meta-content">
        {"".join(sections)}
    </div>
</details>
"""


def _build_legacy_process_payload(items: list[dict]) -> dict:
    payload: dict = {}
    for item in items:
        if not isinstance(item, dict):
            continue

        role = item.get("role")
        content = item.get("content")
        if role == "tool_call_history":
            payload["tool_call_history"] = _coerce_tool_history(content)
        elif role == "search_results_links":
            payload["uris"] = _coerce_list(content)
        elif role == "tool_ocr_extraction":
            payload.setdefault("ocr_results", []).append(content)
        elif role == "enabled_tools":
            payload["enabled_tools"] = _coerce_list(content)
        elif role == "search_keywords":
            payload["search_keywords"] = _coerce_list(content)
        elif role == "thinking_level":
            payload["think_level"] = content
        elif role == "assistant_original_answer":
            payload["assistant_original_answer"] = content
        else:
            payload.setdefault("raw", []).append({"role": role, "content": content})
    return payload


def _coerce_numeric_time(value) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if value in (None, ""):
        return None

    text = str(value).strip()
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return None

    try:
        return float(match.group(1))
    except ValueError:
        return None


def _format_thinking_time(value: float | None) -> str:
    if value is None or value <= 0:
        return ""
    return f"{value:.2f}s"


def _render_tool_history(content) -> str:
    items = _coerce_tool_history(content)
    if not items:
        return _render_data_block(content)

    blocks = []
    for item in items:
        detail_blocks = []
        for key, value in item.items():
            if key == "name":
                continue
            detail_blocks.append(
                f'<div class="kv-item"><div class="kv-key">{html.escape(str(key))}</div>{_render_data_block(value)}</div>'
            )
        detail_html = f'<div class="kv-list">{"".join(detail_blocks)}</div>' if detail_blocks else ""
        blocks.append(
            f'<div class="tool-item"><div><span class="tool-name">{html.escape(str(item.get("name", "tool")))}</span>'
            f'<span class="tool-status">{html.escape(str(item.get("status", "")))}</span></div>{detail_html}</div>'
        )
    return f'<div class="tool-list">{"".join(blocks)}</div>'


def _render_ocr_result(content) -> str:
    if isinstance(content, dict):
        image_path = str(content.get("image_path", ""))
        body = _render_markdown_block(str(content.get("ocr_text", "")))
        image_preview = ""
        if image_path:
            uri = _normalize_image_src(image_path)
            image_preview = f'<div class="image-grid" style="margin-bottom: 10px;"><div class="image-card"><img src="{uri}" alt="OCR 图片"></div></div>'
        return image_preview + body
    return _render_data_block(content)


def _render_link_list(content) -> str:
    links = _coerce_list(content)
    if not links:
        return _render_data_block(content)

    items = []
    for link in links:
        title, href, raw_text = _parse_link_item(link)
        items.append(
            f'<div class="source-item">'
            f'<a class="source-title" href="{href}">{html.escape(title)}</a>'
            f'<div class="source-url">{html.escape(raw_text)}</div>'
            f'</div>'
        )
    return f'<div class="source-list">{"".join(items)}</div>'


def _render_chip_list(content) -> str:
    values = _coerce_list(content)
    if not values and content not in (None, ""):
        values = [content]
    if not values:
        return ""
    chips = "".join(f'<span class="chip">{html.escape(str(value))}</span>' for value in values)
    return f'<div class="chip-list">{chips}</div>'


def _render_list_block(content) -> str:
    values = _coerce_list(content)
    if not values:
        return _render_data_block(content)
    items = "".join(f'<div class="kv-item">{_render_data_block(value)}</div>' for value in values)
    return f'<div class="kv-list">{"".join(items)}</div>'


def _render_data_block(content) -> str:
    if isinstance(content, (list, tuple)):
        return _render_list_block(list(content))
    if isinstance(content, dict):
        parts = []
        for key, value in content.items():
            parts.append(
                f'<div class="kv-item"><div class="kv-key">{html.escape(str(key))}</div>{_render_data_block(value)}</div>'
            )
        return f'<div class="kv-list">{"".join(parts)}</div>'
    return _render_markdown_block("" if content is None else str(content))


def _extract_thinking_time(items: list[dict]) -> str:
    for item in items:
        if item.get("role") != "assistant_thinking_time":
            continue
        content = item.get("content")
        if isinstance(content, (int, float)):
            return f"{content:.2f}s"
        text = str(content).strip()
        match = re.search(r"(\d+(?:\.\d+)?)", text)
        if match:
            return f"{float(match.group(1)):.2f}s"
        return text
    return ""


def _extract_model_name(items: list[dict]) -> str:
    for item in items:
        if item.get("role") == "model":
            content = item.get("content")
            if content not in (None, ""):
                return str(content)
    return ""


def _parse_link_item(link) -> tuple[str, str, str]:
    raw_text = str(link).strip()
    match = re.match(r"^-?\s*\[([^\]]+)\]\(([^)]+)\)\s*$", raw_text)
    if match:
        title = match.group(1).strip()
        url = match.group(2).strip()
        return title or url, _normalize_href(url), url

    href = _normalize_href(raw_text)
    return raw_text, href, raw_text


def _coerce_list(content):
    if isinstance(content, list):
        return content
    if isinstance(content, tuple):
        return list(content)
    if isinstance(content, str):
        stripped = content.strip()
        if not stripped:
            return []
        try:
            parsed = ast.literal_eval(stripped)
            if isinstance(parsed, list):
                return parsed
        except (ValueError, SyntaxError):
            pass
        md_images = re.findall(r'!\[.*?\]\((.*?)\)', stripped)
        if md_images:
            return md_images
    return []


def _coerce_tool_history(content):
    if isinstance(content, list):
        return [item for item in content if isinstance(item, dict)]
    if isinstance(content, str):
        stripped = content.strip()
        if not stripped:
            return []
        try:
            parsed = ast.literal_eval(stripped)
            if isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict)]
        except (ValueError, SyntaxError):
            pass
        matches = re.findall(r'#####\s*name:\s*(.*?),\s*\nstatus:\s*(.*?)(?=\n#####|\Z)', stripped, re.DOTALL)
        return [{"name": name.strip(), "status": status.strip()} for name, status in matches]
    return []


def _path_to_uri(path_str: str) -> str:
    try:
        return Path(path_str).expanduser().resolve().as_uri()
    except Exception:
        return html.escape(path_str, quote=True)


def _normalize_href(href: str) -> str:
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", href):
        return html.escape(href, quote=True)
    if re.match(r"^[a-zA-Z]:[\\/]", href):
        return _path_to_uri(href)
    return html.escape(href, quote=True)


_IMAGE_DATA_URI_CACHE: dict[str, str] = {}


def _normalize_image_src(src: str) -> str:
    raw = html.unescape(str(src or "")).strip()
    if not raw:
        return ""

    data_uri = _to_data_uri_if_local_image(src)
    if data_uri:
        return html.escape(data_uri, quote=True)

    # 图片展示优先走本地绝对 URI，避免相对路径在再次打开历史记录时失效。
    fallback_uri = _local_image_source_to_uri(raw)
    if fallback_uri:
        return fallback_uri
    return _normalize_href(raw)


def _to_data_uri_if_local_image(src: str) -> str:
    path = _resolve_local_image_path(src)
    if path is None:
        return ""

    cache_key = str(path).lower()
    cached = _IMAGE_DATA_URI_CACHE.get(cache_key)
    if cached:
        return cached

    mime_type, _ = mimetypes.guess_type(path.name)
    if not mime_type or not mime_type.startswith("image/"):
        return ""

    try:
        binary = path.read_bytes()
    except OSError:
        return ""

    encoded = base64.b64encode(binary).decode("ascii")
    data_uri = f"data:{mime_type};base64,{encoded}"
    _IMAGE_DATA_URI_CACHE[cache_key] = data_uri
    return data_uri


def _resolve_local_image_path(src: str) -> Path | None:
    raw = html.unescape(str(src or "")).strip()
    if not raw:
        return None

    lowered = raw.lower()
    if lowered.startswith("data:"):
        return None

    if re.match(r"^[a-zA-Z]:[\\/]", raw):
        candidate = Path(raw).expanduser()
    else:
        parsed = urlparse(raw)
        if parsed.scheme and parsed.scheme.lower() not in {"file"}:
            return None

        if parsed.scheme.lower() == "file":
            uri_path = _file_uri_to_path(raw)
            if uri_path is None:
                return None
            candidate = uri_path
        else:
            candidate = Path(raw).expanduser()

    try:
        if not candidate.is_absolute():
            candidate = (Path.cwd() / candidate).resolve()
        else:
            candidate = candidate.resolve()
    except OSError:
        return None

    if not candidate.is_file():
        return None
    return candidate


def _local_image_source_to_uri(src: str) -> str:
    raw = html.unescape(str(src or "")).strip()
    if not raw:
        return ""

    if raw.lower().startswith("data:"):
        return html.escape(raw, quote=True)

    if re.match(r"^[a-zA-Z]:[\\/]", raw):
        return _path_to_uri(raw)

    parsed = urlparse(raw)
    scheme = parsed.scheme.lower()
    if scheme and scheme not in {"file"}:
        return ""

    if scheme == "file":
        file_path = _file_uri_to_path(raw)
        if file_path is None:
            return ""
        return _path_to_uri(str(file_path))

    return _path_to_uri(raw)


def _file_uri_to_path(uri: str) -> Path | None:
    parsed = urlparse(uri)
    if parsed.scheme.lower() != "file":
        return None

    path = unquote(parsed.path or "")
    netloc = parsed.netloc or ""
    if netloc and netloc.lower() != "localhost":
        return Path(f"//{netloc}{path}")

    if re.match(r"^/[a-zA-Z]:", path):
        path = path[1:]
    return Path(path)


def _render_markdown_block(text: str, allow_thematic_break: bool = True) -> str:
    placeholders = {}
    source = text.replace("\r\n", "\n")

    def replace_code_block(match):
        key = f"__CODE_BLOCK_{len(placeholders)}__"
        language = html.escape(match.group(1).strip())
        code = html.escape(match.group(2))
        class_attr = f' class="language-{language}"' if language else ""
        placeholders[key] = f"<pre><code{class_attr}>{code}</code></pre>"
        return key

    source = re.sub(r"```([^\n`]*)\n(.*?)```", replace_code_block, source, flags=re.DOTALL)

    def replace_math_block(match):
        key = f"__MATH_BLOCK_{len(placeholders)}__"
        placeholders[key] = _render_math_mathml(match.group(1), display_mode=True)
        return f"\n{key}\n"

    def replace_math_inline(match):
        key = f"__MATH_BLOCK_{len(placeholders)}__"
        placeholders[key] = _render_math_mathml(match.group(1), display_mode=False)
        return key

    source = re.sub(r"\\\[([\s\S]*?)\\\]", replace_math_block, source)
    source = re.sub(r"\$\$([\s\S]*?)\$\$", replace_math_block, source)
    source = re.sub(r"\\\(([\s\S]*?)\\\)", replace_math_inline, source)

    def replace_single_dollar(match):
        prefix = match.group(1)
        expression = match.group(2)
        return f"{prefix}{_render_math_placeholder(expression, placeholders, display_mode=False)}"

    source = re.sub(r"(^|[^\\])\$(?!\$)([^\n$]*?)\$(?!\$)", replace_single_dollar, source)
    source = html.escape(source)
    source = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', lambda m: _render_inline_image(m.group(1), m.group(2)), source)
    source = re.sub(
        r'\[([^\]]+)\]\(([^)]+)\)',
        lambda m: f'<a href="{_normalize_href(html.unescape(m.group(2)))}">{m.group(1)}</a>',
        source,
    )
    source = re.sub(r'`([^`]+)`', r'<code>\1</code>', source)
    source = re.sub(r'\*\*([^*\n]+)\*\*', r'<strong>\1</strong>', source)
    source = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'<em>\1</em>', source)

    lines = source.split("\n")
    html_parts = []
    paragraph_lines = []
    list_items = []
    list_tag = None
    blockquote_lines = []
    index = 0

    def flush_paragraph():
        nonlocal paragraph_lines
        if paragraph_lines:
            html_parts.append(f"<p>{'<br>'.join(paragraph_lines)}</p>")
            paragraph_lines = []

    def flush_list():
        nonlocal list_items, list_tag
        if list_items and list_tag:
            html_parts.append(f"<{list_tag}>{''.join(list_items)}</{list_tag}>")
        list_items = []
        list_tag = None

    def flush_blockquote():
        nonlocal blockquote_lines
        if blockquote_lines:
            html_parts.append(f"<blockquote>{'<br>'.join(blockquote_lines)}</blockquote>")
            blockquote_lines = []

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            flush_list()
            flush_blockquote()
            index += 1
            continue

        if stripped in placeholders:
            flush_paragraph()
            flush_list()
            flush_blockquote()
            html_parts.append(placeholders[stripped])
            index += 1
            continue

        if index + 1 < len(lines):
            header_candidate = lines[index]
            separator_candidate = lines[index + 1]
            if _looks_like_markdown_table(header_candidate, separator_candidate):
                flush_paragraph()
                flush_list()
                flush_blockquote()

                table_rows = [header_candidate, separator_candidate]
                row_index = index + 2
                while row_index < len(lines):
                    row_line = lines[row_index]
                    row_stripped = row_line.strip()
                    if not row_stripped:
                        break
                    if row_stripped in placeholders:
                        break
                    if not _is_markdown_table_row(row_line):
                        break
                    table_rows.append(row_line)
                    row_index += 1

                html_parts.append(_render_markdown_table(table_rows))
                index = row_index
                continue

        if allow_thematic_break and _is_markdown_thematic_break(stripped):
            flush_paragraph()
            flush_list()
            flush_blockquote()
            html_parts.append("<hr>")
            index += 1
            continue

        heading_match = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if heading_match:
            flush_paragraph()
            flush_list()
            flush_blockquote()
            level = len(heading_match.group(1))
            html_parts.append(f"<h{level}>{heading_match.group(2)}</h{level}>")
            index += 1
            continue

        quote_match = re.match(r"^&gt;\s?(.*)$", stripped)
        if quote_match:
            flush_paragraph()
            flush_list()
            blockquote_lines.append(quote_match.group(1))
            index += 1
            continue

        flush_blockquote()

        ul_match = re.match(r"^[-*]\s+(.*)$", stripped)
        ol_match = re.match(r"^\d+\.\s+(.*)$", stripped)
        if ul_match or ol_match:
            flush_paragraph()
            tag = "ul" if ul_match else "ol"
            item = ul_match.group(1) if ul_match else ol_match.group(1)
            if list_tag not in (None, tag):
                flush_list()
            list_tag = tag
            list_items.append(f"<li>{item}</li>")
            index += 1
            continue

        flush_list()
        paragraph_lines.append(stripped)
        index += 1

    flush_paragraph()
    flush_list()
    flush_blockquote()

    rendered = "".join(html_parts)
    for key, value in placeholders.items():
        rendered = rendered.replace(key, value)
    return f'<div class="message-content">{rendered}</div>'


def _split_markdown_table_row(line: str) -> list[str]:
    raw = str(line or "").strip()
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|"):
        raw = raw[:-1]
    return [cell.strip() for cell in raw.split("|")]


def _is_markdown_table_row(line: str) -> bool:
    row = str(line or "").strip()
    return "|" in row and not row.startswith("#") and not row.startswith("&gt;")


def _is_markdown_thematic_break(line: str) -> bool:
    stripped = str(line or "").strip()
    return re.match(r"^([-*_])(?:\s*\1){2,}$", stripped) is not None


def _looks_like_markdown_table(header_line: str, separator_line: str) -> bool:
    if not _is_markdown_table_row(header_line):
        return False
    sep_cells = _split_markdown_table_row(separator_line)
    if not sep_cells:
        return False
    for cell in sep_cells:
        if not re.match(r"^:?-{3,}:?$", cell):
            return False
    return True


def _render_markdown_table(lines: list[str]) -> str:
    header_cells = _split_markdown_table_row(lines[0])
    align_cells = _split_markdown_table_row(lines[1]) if len(lines) > 1 else []
    body_lines = lines[2:] if len(lines) > 2 else []
    col_count = max(len(header_cells), len(align_cells), *(len(_split_markdown_table_row(row)) for row in body_lines), 1)

    def resolve_align(cell: str) -> str:
        cell = cell.strip()
        if cell.startswith(":") and cell.endswith(":"):
            return "center"
        if cell.endswith(":"):
            return "right"
        return "left"

    alignments = [resolve_align(align_cells[idx]) if idx < len(align_cells) else "left" for idx in range(col_count)]

    def to_cells(cells: list[str], tag: str) -> str:
        normalized = cells + [""] * (col_count - len(cells))
        html_cells = []
        for idx, value in enumerate(normalized):
            align = alignments[idx] if idx < len(alignments) else "left"
            html_cells.append(f'<{tag} style="text-align:{align};">{value}</{tag}>')
        return "".join(html_cells)

    header_html = f"<thead><tr>{to_cells(header_cells, 'th')}</tr></thead>"
    body_html = ""
    if body_lines:
        body_rows = []
        for row in body_lines:
            row_cells = _split_markdown_table_row(row)
            body_rows.append(f"<tr>{to_cells(row_cells, 'td')}</tr>")
        body_html = f"<tbody>{''.join(body_rows)}</tbody>"
    return f"<table>{header_html}{body_html}</table>"


def _render_math_placeholder(expression: str, placeholders: dict, display_mode: bool) -> str:
    key = f"__MATH_BLOCK_{len(placeholders)}__"
    placeholders[key] = _render_math_mathml(expression, display_mode=display_mode)
    return key


def _render_math_mathml(expression: str, display_mode: bool) -> str:
    source = str(expression or "").strip()
    if not source:
        return ""

    try:
        mathml = latex_to_mathml(source)
    except Exception:
        fallback = html.escape(source)
        class_name = "math-block" if display_mode else "math-inline"
        return f'<span class="{class_name}">{fallback}</span>'

    class_name = "math-block" if display_mode else "math-inline"
    return f'<div class="{class_name}">{mathml}</div>' if display_mode else f'<span class="{class_name}">{mathml}</span>'


def _render_inline_image(alt: str, src: str) -> str:
    real_src = html.unescape(src)
    uri = _normalize_image_src(real_src)
    alt_text = html.escape(html.unescape(alt))
    return f'<span class="image-card" style="display:block;margin:12px 0;"><img src="{uri}" alt="{alt_text}"></span>'
