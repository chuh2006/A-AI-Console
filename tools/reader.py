import json
import os
import re


def _resolve_history_path(file_name: str) -> str:
    safe_name = os.path.basename(str(file_name or "").strip())
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    chat_result_dir = os.path.join(parent_dir, "chat_result")
    chat_result_json_dir = os.path.join(chat_result_dir, "json")

    stem, suffix = os.path.splitext(safe_name)
    suffix = suffix.lower()
    candidates: list[str] = []

    if suffix == ".html":
        candidates.extend(
            [
                os.path.join(chat_result_json_dir, f"{stem}.json"),
                os.path.join(chat_result_dir, f"{stem}.json"),
                os.path.join(chat_result_dir, safe_name),
            ]
        )
    elif suffix == ".json":
        candidates.extend(
            [
                os.path.join(chat_result_json_dir, safe_name),
                os.path.join(chat_result_dir, safe_name),
            ]
        )
    elif suffix == ".md":
        candidates.append(os.path.join(chat_result_dir, safe_name))
    else:
        candidates.extend(
            [
                os.path.join(chat_result_json_dir, f"{safe_name}.json"),
                os.path.join(chat_result_dir, f"{safe_name}.json"),
                os.path.join(chat_result_dir, f"{safe_name}.html"),
                os.path.join(chat_result_dir, f"{safe_name}.md"),
            ]
        )

    for path in candidates:
        if os.path.exists(path):
            return path

    return candidates[0] if candidates else os.path.join(chat_result_dir, safe_name)


def read_from_history(file_name: str) -> tuple[list[dict], float, list[dict]]:
    """
    读取会话历史文件。
    Args:
        file_name: 要读取的历史文件名（位于 chat_result 目录下）

    Returns:
        (对话列表, temperature 值, 完整历史)
    """
    safe_name = os.path.basename(str(file_name or "").strip())
    file_path = _resolve_history_path(safe_name)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"文件 {safe_name} 未找到，请确认它位于 chat_result 目录下。")
        return read_from_history(input("请输入正确的文件名: "))

    if file_path.lower().endswith(".json"):
        return _read_from_json(content)

    return _read_from_markdown(content)


def _read_from_json(content: str) -> tuple[list[dict], float, list[dict]]:
    full_history = json.loads(content)
    if not isinstance(full_history, list):
        raise ValueError("历史记录 JSON 格式错误：根节点必须是 list。")

    messages = []
    temperature = 1.0

    for item in full_history:
        if not isinstance(item, dict):
            continue

        role = item.get("role")
        text = item.get("content", "")

        if role in {"system", "user", "assistant", "tool"}:
            messages.append(dict(item))
        elif role == "assistant_tool_calls":
            assistant_record = dict(item)
            assistant_record["role"] = "assistant"
            messages.append(assistant_record)
        elif role == "assistant_answer":
            messages.append({
                "role": "assistant",
                "content": text,
            })
        elif role == "temperature":
            try:
                temperature = float(text)
            except (TypeError, ValueError):
                temperature = 1.0

    return messages, temperature, full_history


def _read_from_markdown(content: str) -> tuple[list[dict], float, list[dict]]:
    messages = []
    full_history = []
    temperature = 1.0

    pattern = r'# <span style="background-color:yellow;">([^<]+)</span>\s*\n(.*?)(?=\n# <span style="background-color:yellow;">|$)'
    matches = re.findall(pattern, content, re.DOTALL)

    for title, text in matches:
        title = title.strip()
        text = text.strip()

        role_name = title.rstrip(":")
        if role_name == "user" and text.startswith("```") and text.endswith("```"):
            text = text[3:-3].strip()

        full_history.append({
            "role": role_name,
            "content": text,
        })

        if title == "system:":
            messages.append({
                "role": "system",
                "content": text,
            })
        elif title == "user:":
            text_processed = text
            if text_processed.startswith("```") and text_processed.endswith("```"):
                text_processed = text_processed[3:-3].strip()
            messages.append({
                "role": "user",
                "content": text_processed,
            })
        elif title == "assistant:":
            messages.append({
                "role": "assistant",
                "content": text,
            })
        elif title == "tool:":
            messages.append({
                "role": "tool",
                "content": text,
            })
        elif title == "assistant_answer:":
            messages.append({
                "role": "assistant",
                "content": text,
            })
        elif title == "assistant_tool_calls:":
            messages.append({
                "role": "assistant",
                "content": text,
            })
        elif title == "temperature:":
            try:
                temperature = float(text)
            except ValueError:
                temperature = 1.0

    return messages, temperature, full_history
