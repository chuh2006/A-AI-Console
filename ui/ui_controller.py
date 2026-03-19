import time
import itertools
import threading
from typing import Generator, Dict, Any, Tuple, List
import os

class UIController:
    def __init__(self):
        self._spinner_registry = []
        self.model_map = {
            "0": "自己回答",
            "1": "deepseek-chat",
            "2": "deepseek-reasoner",
            "3": "multi-assistant",
            "4": "帮我选择",
            "5": "错误消息",
            "6": "math-model",
            "7": "gemini-3.1-flash-lite-preview",
            "8": "gemini-3-flash-preview",
            "9": "gemini-3.1-pro-preview",
            "10": "qwen3.5-plus"
            }

    def get_user_input(self, prompt: str = "请输入文本：") -> str:
        return input(prompt).strip()
    
    def get_model_choice(self) -> str:
        menu = (
            "可用模型：\n"
            "0:自己回答 \n1:DeepSeek V3.2 Chat\n2:DeepSeek V3.2 Reasoner \n"
            "3:multi-assistant \n4:帮我选择 \n5:错误消息 \n6:数学模型 \n"
            "7:Gemini 3.1 Flash-Lite Preview \n8:Gemini 3 Flash Preview\n"
            "9:Gemini 3.1 Pro Preview\n10:Qwen 3.5 Plus\n请输入文本> "
        )
        choice = input(menu).strip()
        try:
            if int(choice) not in range(0, 11):
                raise ValueError
        except ValueError:
            self.display_warning("无效的选择，请重新选择。")
            return self.get_model_choice()  # 递归调用直到用户输入有效选项
        return self.model_map.get(choice, "deepseek-chat")  # 默认使用 deepseek-chat
    
    def get_image_input(self, model_name: str) -> List[str]:
        is_image = input("是否输入图片[y/N]：").strip().lower() == 'y'
        if not is_image:
            return []

        path_list = []
        if "qwen" in model_name:
            # Qwen 目前在 OpenAI 兼容模式下仅支持 URL
            image_path = input("仅支持网图，请输入图片URL(多个用逗号分隔)：").replace('"', '').replace("'", "")
            path_list = [p.strip() for p in image_path.replace('，', ',').split(',') if p.strip()]
        elif "gemini" in model_name:
            # Gemini 支持本地文件
            image_path = input("请输入图片本地文件路径(多个用逗号分隔)：").replace('"', '').replace("'", "")
            raw_paths = [p.strip() for p in image_path.replace('，', ',').split(',') if p.strip()]
            
            # 这里调用你在原文件里的文件存在性检查逻辑
            for p in raw_paths:
                if os.path.exists(p):
                    path_list.append(p)
                else:
                    self.display_warning(f"无法读取图片文件：{p}，请检查路径。")
        elif "deepseek" in model_name:
            image_path = input("请输入图片本地文件路径(多个用逗号分隔)：").replace('"', '').replace("'", "")
            raw_paths = [p.strip() for p in image_path.replace('，', ',').split(',') if p.strip()]
            for p in raw_paths:
                if os.path.exists(p):
                    path_list.append(p)
                else:
                    self.display_warning(f"无法读取图片文件：{p}，请检查路径。")
        else:
            self.display_warning(f"当前模型 {model_name} 暂不支持图片输入。")
            
        return path_list
    
    def get_boolean_input(self, prompt: str) -> bool:
        """通用的 Yes/No 询问器"""
        return input(f"{prompt}[y/N]: ").strip().lower() == 'y'
    
    def render_stream(self, stream: Generator[Dict[str, Any], None, None]) -> Tuple[str, str, Dict]:
        """
        消费底层 LLM 传来的流式数据，负责优雅地打印到终端。
        返回 (最终答案, 思考过程, 元数据字典)
        """
        print("助手：", end="", flush=True)
        
        final_answer = ""
        thought_content = ""
        meta_info = {}
        is_thinking = False
        is_first_content = True
        meta_info = {"ocr_results": []} # 专门开辟一个列表放 OCR 记录

        for chunk in stream:
            chunk_type = chunk.get("type")
            content = chunk.get("content", "")

            if chunk_type == "meta_ocr":
                # 将 OCR 结果暂存在 meta 中
                meta_info["ocr_results"].append({
                    "image_path": chunk["image_path"], 
                    "ocr_text": chunk["ocr_text"]
                })

            elif chunk_type == "thinking":
                is_thinking = True
                print(content, end="", flush=True)
                thought_content += content

            elif chunk_type == "content":
                # 如果刚才还在思考，现在开始输出正文了，打印一条绿色分割线
                if is_thinking and is_first_content:
                    # 这里的耗时会在流结束后通过 meta 传来，但为了体验，可以在这里打印分割线
                    print(f"\n\033[92m思考结束，开始回答...\033[0m\n", end="")
                    is_thinking = False
                    is_first_content = False
                    
                print(content, end="", flush=True)
                final_answer += content

            elif chunk_type == "meta":
                meta_info.update(chunk)

            elif chunk_type == "system":
                # 打印系统级别的提示（比如上传图片的进度）
                print(f"\033[94m[S] {content}\033[0m", end="", flush=True)

        print("\n", end="") # 流结束换行
        
        # 补充打印耗时信息
        thinking_time = meta_info.get("thinking_time", -1.0)
        if thinking_time > 0:
            print(f"\033[90m(总耗时: {thinking_time:.2f}秒)\033[0m")
            
        return final_answer, thought_content, meta_info
    
    def display_warning(self, msg: str):
        """标准化的警告输出（黄色）"""
        print(f"\033[93m[W] {msg}\033[0m")

    def display_error(self, msg: str):
        """标准化的错误输出（红色）"""
        print(f"\033[91m[E] {msg}\033[0m")

    def display_system(self, msg: str):
        """标准化的系统提示（蓝色）"""
        print(f"\033[94m[S] {msg}\033[0m")

    def start_spinner(self, msg: str = "处理中", delay: float = 0.12) -> threading.Event:
        stop_event = threading.Event()
        
        def _spin():
            for ch in itertools.cycle("/-\\|"):
                if stop_event.is_set():
                    break
                print(f"\r{msg} {ch}", end="", flush=True)
                time.sleep(delay)
            # 清理行
            print("\r" + " " * (len(msg) + 2) + "\r", end="", flush=True)
            
        t = threading.Thread(target=_spin, daemon=True)
        t.start()
        self._spinner_registry.append((stop_event, t))
        return stop_event

    def stop_all_spinners(self):
        for stop_event, thread in list(self._spinner_registry):
            stop_event.set()
            if thread.is_alive():
                try:
                    thread.join(timeout=0.5)
                except Exception:
                    pass
        self._spinner_registry.clear()