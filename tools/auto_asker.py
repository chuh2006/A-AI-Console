import re
from openai import OpenAI
import tools.prompts as prompts
from tools.costum_expections import AutoAskerException

def get_question(api_key: str, message: list[dict]) -> str:
    """
    调用 DeepSeek 生成一个问题，作为 Auto Asker 的输出。
    """
    if not api_key:
        return ""
        
    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )

        messages = [
            {"role": "system", "content": prompts.Prompts.auto_asker_system_prompt},
            {"role": "user", "content": prompts.Prompts.auto_asker_first_prompt_user},
            *message
            ]
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=1
        )

        question = response.choices[0].message.content.strip()
        return question
    
    except Exception as e:
        print(f"自动提问生成失败: {e}")
        raise AutoAskerException(f"自动提问生成失败: {e}")