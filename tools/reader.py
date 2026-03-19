import os
import re

def read_from_history(file_name: str) -> tuple[list[dict], float, list[dict]]:
    """
    读取markdown格式的对话历史文件
    
    Args:
        file_name: 要读取的md文件名（在chat_result目录下）
        
    Returns:
        tuple[list[dict], float, list[dict]]: (对话列表, temperature值, 完整历史)
        对话列表格式: [{"role": "system/user/assistant", "content": "..."}]
        完整历史格式: [{"role": "标题名", "content": "内容"}]
    """
    # 构建完整文件路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    file_path = os.path.join(parent_dir, "chat_result", file_name)
    
    # 读取文件内容
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"文件 {file_name} 未找到。请确保文件存在于 chat_result 目录下。")
        return read_from_history(input("请输入正确的文件名: "))
    except Exception as e:
        raise e

    # 用于存储结果
    messages = []
    full_history = []
    temperature = 1.0  # 默认值
    
    # 正则表达式匹配标题格式: # <span style="background-color:yellow;">xxx:</span>
    pattern = r'# <span style="background-color:yellow;">([^<]+)</span>\s*\n(.*?)(?=\n# <span style="background-color:yellow;">|$)'
    
    # 找到所有匹配的标题和内容
    matches = re.findall(pattern, content, re.DOTALL)

    system = ""
    
    for title, text in matches:
        title = title.strip()
        text = text.strip()
        
        # 将所有标题和内容添加到完整历史中（去除标题中的冒号）
        role_name = title.rstrip(':')
        if role_name == 'user':
            if text.strip().startswith('```') and text.strip().endswith('```'):
                text = text.strip()[3:-3].strip()
        full_history.append({
            "role": role_name,
            "content": text
        })
        
        # 处理对话消息
        if title == 'system:':
            messages.append({
                "role": "system",
                "content": text
            })
            system = text
        elif title == 'user:':
            # 去除两端的 ```
            text_processed = text.strip()
            if text_processed.startswith('```') and text_processed.endswith('```'):
                # 去除开头的 ```
                text_processed = text_processed[3:]
                # 去除结尾的 ```
                text_processed = text_processed[:-3]
                text_processed = text_processed.strip()
            messages.append({
                "role": "user",
                "content": text_processed
            })
        elif title == 'assistant_answer:':
            messages.append({
                "role": "assistant",
                "content": text
            })
        # 处理temperature
        elif title == 'temperature:':
            try:
                temperature = float(text)
            except ValueError:
                temperature = 1.0
    
    return messages, temperature, full_history
