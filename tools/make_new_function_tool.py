import json
import os
import re
from openai import OpenAI
from tools.prompts import Prompts


def _extract_json_text(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        raise ValueError("AI 返回内容为空")

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError(f"AI 返回的内容不是有效 JSON: {text[:200]}")

    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("AI 返回的 JSON 不是对象类型")
    return data

create_new_tool_schema = {
    "type": "function",
    "function": {
        "name": "create_tool",
        "description": "有时程序提供的工具不能够满足用户的需求，这时你可以创建一个新的工具。请根据用户的需求描述，设计一个新的工具，并提供必要的参数信息。",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "要创建的工具的名称"
                },
                "description": {
                    "type": "string",
                    "description": "详细描述工具的功能和实现方式，以便程序生成并使用该工具"
                },
            },
            "required": ["name", "description"]
        }
    }
}

def create_new_tool(api_key: str, name: str, description: str) -> dict:
    """调用AI模型按规范生成工具"""
    if not api_key:
        return {"result": "error", "message": "API key is required to create a new tool."}
    
    try:
        allowance = input(f"模式请求创建新工具 '{name}'，描述: {description}。是否允许？[y/N]: ")
        if allowance.lower() not in ['y', 'yes']:
            raise Exception("用户拒绝创建工具。")

        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        context = [
            {"role": "system", "content": Prompts.tool_creator_prompt},
            {"role": "user", "content": f"请根据以下工具需求描述，设计一个新的工具，并提供必要的参数信息。\n工具名称:\n{name}\n\n工具需求描述: \n{description}\n\n务必按要求以json格式回复"}
        ]

        response = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=context,
            response_format={
                'type': 'json_object'
            },
            temperature=0.8
        )
        tool_info = response.choices[0].message.content if response.choices else ""
        tool_info_json = _extract_json_text(tool_info)
        ret = {
            "result": "success",
            "message": f"工具 '{name}' 创建成功。",
            "schema": tool_info_json.get("schema", {}),
            "function": tool_info_json.get("function", "")
        }
        return ret

    except Exception as e:
        return {"result": "error", "message": f"创建工具时发生错误 - {str(e)}"}