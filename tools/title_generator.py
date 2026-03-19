import re
from openai import OpenAI
import tools.prompts as prompts

def generate_auto_title(api_key: str, user_input: str) -> str:
    """
    根据用户的第一句话，调用 DeepSeek 快速生成一个简短的文件标题。
    """
    if not api_key:
        return ""
        
    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        
        # 组装原来你定义的 prompt
        context = [
            {"role": "system", "content": prompts.Prompts.title_spawner_prompt},
            {"role": "user", "content": f"请根据用户的请求生成一个简洁的标题。用户的请求是：{user_input}"}
        ]
        
        # 使用普通的阻塞请求（不需要流式）
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=context,
            temperature=0.5
        )
        
        title = response.choices[0].message.content.strip()
        
        # 剔除无效字符并限制长度
        if '标题生成' in title:
            title = ""
        else:
            title = title[:15] if len(title) > 15 else title
            title = re.sub(r'[\\/*?:"<>|.]', '', title)
            
        return title
    except Exception as e:
        # 如果标题生成失败，不应该影响主流程，直接静默返回空字符串
        print(f"自动标题生成失败: {e}")
        return ""