import json
import os
import re
from datetime import datetime
import tools.prompts as prompts
import tools.auto_asker as auto_asker

class ChatSession:
    def __init__(self, system_prompt: str = "", first_time: bool = True, enable_system_prompt: bool = True):
        self.history = []          # 发给 API 的历史 (OpenAI 格式)
        self.full_context = []     # 用于本地保存的完整上下文
        self.full_context.append({"role": "directions", "content": prompts.Prompts.directions})
        if system_prompt and enable_system_prompt:
            self.history.append({"role": "system", "content": system_prompt})
            self.full_context.append({"role": "system", "content": system_prompt})

    def get_asker_context(self) -> list[dict]:
        context = []
        role_map = {"user": "assistant", "assistant": "user"}
        for msg in self.history:
            if msg["role"] in ["user", "assistant"]:
                context.append({"role": role_map[msg["role"]], "content": msg["content"]})
        return context
    
    def get_question(self, api_key: str) -> str:
        asker_context = self.get_asker_context()
        if not asker_context:
            return ""
        question = auto_asker.get_question(api_key, asker_context)
        return question

    def add_epoch_count(self, epoch: int):
        """记录当前轮次，格式为 epoch_count: {epoch}"""
        self.full_context.append({"role": "epoch_count", "content": str(epoch)})

    def add_user_message(self, content: str, original_text: str = None, images: list = None):
        """记录用户输入，包括原始文本和图片"""
        # 1. 保存图片到日志 (Markdown格式)
        if images:
            img_md_lists = [f"![img{i+1}]({path})" for i, path in enumerate(images)]
            self.full_context.append({"role": "image_uploaded", "content": "\n".join(img_md_lists)})
        # 2. 如果文本被随机化处理了，保存一份原始的
        if original_text and original_text != content:
            self.full_context.append({"role": "user_original", "content": original_text})
        
        self.history.append({"role": "user", "content": content})
        self.full_context.append({"role": "user", "content": content})
        self._auto_clean_context()
    
    def add_enabled_tools(self, tools: list[str]):
        """记录本轮对话中启用的工具列表"""
        if tools:
            self.full_context.append({"role": "enabled_tools", "content": str(tools)})

    def add_assistant_message(self, content: str, original_content: str = None, thinking: str = "", model_name: str = "", meta: dict = None):
        """记录助手输出，包括元数据（耗时、搜索链接、思考等级）和随机化前的原文本"""
        self.history.append({"role": "assistant", "content": content})
        
        # 写入各种元数据到 full_context
        if model_name:
            self.full_context.append({"role": "model", "content": model_name})
        
        if meta:
            if meta.get("uris"):
                self.full_context.append({"role": "search_results_links", "content": str(meta.get("uris"))})
            if meta.get("think_level"):
                self.full_context.append({"role": "thinking_level", "content": meta.get("think_level")})
            if meta.get("ocr_results"):
                for ocr_item in meta["ocr_results"]:
                    ocr_log = f"**读取目标:** `{ocr_item['image_path']}`\n**提取结果:**\n```text\n{ocr_item['ocr_text']}\n```"
                    self.full_context.append({"role": "tool_ocr_extraction", "content": ocr_log})
            if meta.get("search_keywords"):
                self.full_context.append({"role": "search_keywords", "content": str(meta.get("search_keywords"))})
            
        if thinking:
            self.full_context.append({"role": "assistant_thinking", "content": thinking})
            
        if meta and meta.get("thinking_time", -1) > 0:
            self.full_context.append({"role": "assistant_thinking_time", "content": f"{meta['thinking_time']:.2f} seconds"})

        # 如果回答被随机化处理了，保存一份原始的
        if original_content and original_content != content:
            self.full_context.append({"role": "assistant_original_answer", "content": original_content})
            
        self.full_context.append({"role": "assistant_answer", "content": content})
        self._auto_clean_context()

    def rollback_last_user_message(self):
        """如果请求彻底失败且用户放弃重试，将最后一条用户消息从历史中弹出，防止污染下一次对话"""
        if self.history and self.history[-1]["role"] == "user":
            self.history.pop()

    def get_history(self) -> list:
        return self.history.copy()

    def _calc_token_count(self) -> int:
        # 你的估算逻辑：英文 0.3，非 ASCII 0.6
        count = 0
        for msg in self.history:
            for char in msg.get("content", ""):
                count += 0.6 if ord(char) > 127 else 0.3
        return int(count)

    def _auto_clean_context(self):
        # 超过 128k Token 时，删除最早的一轮对话 (保留 system prompt)
        while self._calc_token_count() >= 128000 and len(self.history) > 3:
            self.history = [self.history[0]] + self.history[3:]

    def save_to_disk(self, title: str):
        if title:
            # Normalize any user-provided path-like title to a safe filename stem.
            safe_title = os.path.basename(title.strip())
            safe_title = os.path.splitext(safe_title)[0]
            safe_title = re.sub(r'[\\/*?:"<>|]', '', safe_title)
            title = safe_title.strip()

        if not title:
            title = "chat_" + datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        
        os.makedirs("chat_result", exist_ok=True)
        base_filepath = f"chat_result/{title}"
        counter = 1
        filepath = base_filepath

        while os.path.exists(f"{filepath}.md"):
            filepath = f"{base_filepath}({counter})"
            counter += 1
        
        filepath += ".md"
        with open(filepath, "w", encoding="utf-8") as f:
            for msg in self.full_context:
                content = msg['content']
                if 'user' in msg['role']:
                    content = f"```\n{content}\n```"
                f.write(f"# <span style=\"background-color:yellow;\">{msg['role']}:</span>\n{content}\n")
        return filepath