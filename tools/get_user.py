get_user_schema = {
    "type": "function",
    "function": {
        "name": "get_user",
        "description": "有时用户提供的消息可能不完整或者不清晰，你可以调用这个工具来获取用户的进一步输入，以便更好地理解用户的需求。",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "简洁明了你需要询问用户的内容，以问句形式呈现。"
                },
                "type": {
                    "type": "string",
                    "description": "你最希望用户提供什么样的信息，例如“阐明需求”，“补充细节”，“提供示例”等等，也就是需要用户做{type}"
                },
                "missing_param": {
                    "type": "string",
                    "description": "如果你觉得用户的输入缺少了某个关键信息或者参数，请在这里指出来，明确告诉用户缺少了什么，也就是需要用户提供{missing_param}"
                },
                "options": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "description": "选项内容"
                    },
                    "description": "[可选] 如果你希望用户从几个选项中选择一个，请在这里列出这些选项。"
                }
            },
            "required": ["question", "type", "missing_param"]
        }
    }
}

def get_user(question: str, input_type: str, missing_param: str, options: list = None) -> dict:
    """调用这个函数来获取用户的进一步输入，以便更好地理解用户的需求。"""
    if options:
        print(f"\n{question}")
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")
        choice = input("请选择一个选项 (输入序号)> ")
        while True:
            if choice.isdigit() and 1 <= int(choice) <= len(options):
                selected_option = options[int(choice) - 1]
                return {"result": "success", "user_input": selected_option}
            else:
                choice = input("无效输入，请输入有效的选项序号> ")
    else:
        user_input = input(f"\n模型需要你{input_type}\n{question}\n请填入{missing_param}(留空以拒绝)> ")
        if user_input.strip() == "" or not user_input.strip():
            return {"result": "reject", "message": "用户拒绝回答问题"}
        return {"result": "success", "user_input": user_input}