"""
由于某些模型自我意识过剩，认为自己训练时的时间是当前时间，并且不相信时效性内容，认为是未来发生的虚构事件
"""
from datetime import datetime

def get_time(description: str = None) -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

time_tool_schema = {
    "type": "function",
    "function": {
        "name": "get_time",
        "description": "获取用户所在时区的当前时间，只要你需要获取当前时间就优先调用这个函数。避免使用网络搜索浪费资源",
        "parameters": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "无意义，满足tool_schema规范，你在这里随意输入一个字符串即可，不会影响返回的时间，举例:`test`"
                }
            },
            "required": ["description"]
        }
    }
}
