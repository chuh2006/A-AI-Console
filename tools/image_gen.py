from typing import Any


image_gen_tool_schema = {
    "type": "function",
    "function": {
        "name": "image_gen",
        "description": (
            "当用户明确要求生成、绘制、设计或改图时调用。"
            "工具只接收你整理好的生图提示词；系统会在后台交给 Seedream 生成图片。"
            "调用成功代表生图任务已经提交，图片生成完成后会自动展示给用户。"
            "由于生图模型看不到对话历史，所以在需要时必须为模型提供完整的上下文信息。"
            "向用户说明时不要用“已经提交请求了”这样的表述，应该用“下面是为你生成的图片”这种说法。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "完整、具体、可直接交给生图模型的提示词。应包含主体、场景、风格、构图、文字要求和约束。",
                }
            },
            "required": ["prompt"],
        },
    },
}


def build_image_gen_tool_result(job_id: str, requested_count: int, model: str) -> str:
    return (
        "Success: 生图任务已成功提交给 Seedream。"
        f"任务ID: {job_id}；模型: {model}；预计生成 {max(1, int(requested_count or 1))} 张图片。"
        "你可以继续正常回复用户，不需要等待图片完成；图片完成后系统会自动展示。"
    )


def coerce_image_prompt(arguments: Any) -> str:
    if isinstance(arguments, dict):
        return str(arguments.get("prompt", "") or "").strip()
    return str(arguments or "").strip()
