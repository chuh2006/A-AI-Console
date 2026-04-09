import json

think_abstract_schema = {
    "type": "function",
    "function": {
        "name": "think_abstract",
        "description": "[仅可在思考中调用] 作为长思考模型，你的思考会分为多个阶段，如果全部显示可能影响用户观感。通过该工具反馈给用户你接下来一段时间思考的重点和方向，从而提升用户体验。如果看到此工具你必须首先调用，再进行思考。仅在思考过程中可调用该工具。该工具不会计入工具调用次数限制。",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "简洁明了展示你接下来思考的方向，作为用户看到的未展开状态的摘要"
                },
                "abstract": {
                    "type": "string",
                    "description": "详细展示你接下来思考的重点和方向，作为用户看到的展开状态的摘要"
                }
            },
            "required": ["title", "abstract"]
        }
    }
}

def think_abstract(ai_return: str) -> dict:
    ai_return_dict = json.loads(ai_return)
    title = ai_return_dict.get("title", "")
    abstract = ai_return_dict.get("abstract", "")
    return {"title": title, "abstract": abstract}