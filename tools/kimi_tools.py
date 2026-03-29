from typing import Any, Dict

kimi_web_search_tool_schema = {
		"type": "builtin_function",  # <-- 我们使用 builtin_function 来表示 Kimi 内置工具，也用于区分普通 function
		"function": {
			"name": "$web_search",
		},
	}

def search_impl(arguments: Dict[str, Any]) -> dict:
    """
    在使用 Moonshot AI 提供的 search 工具的场合，只需要原封不动返回 arguments 即可，
    不需要额外的处理逻辑。
 
    但如果你想使用其他模型，并保留联网搜索的功能，那你只需要修改这里的实现（例如调用搜索
    和获取网页内容等），函数签名不变，依然是 work 的。
 
    这最大程度保证了兼容性，允许你在不同的模型间切换，并且不需要对代码有破坏性的修改。
    """
    print(f"调用了 search_impl，接收的 arguments: {arguments}\n类型：{type(arguments)}") # debug
    return {"arguments": arguments}