import json
import os
import re


def read_from_history(file_name: str) -> tuple[list[dict], float, list[dict]]:
    """
    读取会话历史文件。

    Args:
        file_name: 要读取的历史文件名（位于 chat_result 目录下）

    Returns:
        (对话列表, temperature 值, 完整历史)
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    chat_result_dir = os.path.join(parent_dir, "chat_result")
    file_path = os.path.join(chat_result_dir, file_name)

    if file_path.lower().endswith(".html"):
        paired_json_path = os.path.splitext(file_path)[0] + ".json"
        if os.path.exists(paired_json_path):
            file_path = paired_json_path

    if not os.path.exists(file_path) and not os.path.splitext(file_name)[1]:
        json_path = os.path.join(chat_result_dir, f"{file_name}.json")
        html_path = os.path.join(chat_result_dir, f"{file_name}.html")
        md_path = os.path.join(chat_result_dir, f"{file_name}.md")
        if os.path.exists(json_path):
            file_path = json_path
        elif os.path.exists(html_path):
            paired_json_path = os.path.splitext(html_path)[0] + ".json"
            file_path = paired_json_path if os.path.exists(paired_json_path) else html_path
        elif os.path.exists(md_path):
            file_path = md_path

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"文件 {file_name} 未找到。请确保文件存在于 chat_result 目录下。")
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

        if role == "system":
            messages.append({
                "role": "system",
                "content": text
            })
        elif role == "user":
            messages.append({
                "role": "user",
                "content": text
            })
        elif role == "assistant_answer":
            messages.append({
                "role": "assistant",
                "content": text
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
            "content": text
        })

        if title == "system:":
            messages.append({
                "role": "system",
                "content": text
            })
        elif title == "user:":
            text_processed = text
            if text_processed.startswith("```") and text_processed.endswith("```"):
                text_processed = text_processed[3:-3].strip()
            messages.append({
                "role": "user",
                "content": text_processed
            })
        elif title == "assistant_answer:":
            messages.append({
                "role": "assistant",
                "content": text
            })
        elif title == "temperature:":
            try:
                temperature = float(text)
            except ValueError:
                temperature = 1.0

    return messages, temperature, full_history
