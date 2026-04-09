plan_tool_schema = {
    "type": "function",
    "function": {
        "name": "plan",
        "description": "收到用户输入后，如果是一个复杂的任务或者问题，请你先制定一个清晰的计划，列出你打算如何一步步调用不同工具来解决问题，",
        "parameters": {
            "type": "object",
            "properties": {
                "goals": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": ["goals"]
        }
    }
}