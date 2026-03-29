import time
import itertools
import threading
from typing import Generator, Dict, Any, Tuple, List
import os
import uuid
import hashlib
import io
from datetime import datetime
from PIL import ImageGrab, Image
import shutil
from tools.documents_reader import DocumentParser, UnsupportedFileFormatError

class UIController:
    def __init__(self):
        self._spinner_registry = []
        self.model_map = {
            "0": "自己回答",
            "1": "default",
            "2": "deepseek",
            "3": "multi-assistant",
            "4": "帮我选择",
            "5": "错误消息",
            "6": "math-model",
            "7": "gemini-3.1-flash-lite-preview",
            "8": "gemini-3-flash-preview",
            "9": "gemini-3.1-pro-preview",
            "10": "qwen3.5-plus",
            "11": "doubao-seed-2-0-pro-260215",
            "12": "doubao-seed-2-0-lite-260215",
            "13": "doubao-seed-2-0-mini-260215"
            }

    def get_user_input(self, prompt: str = "请输入文本：") -> str:
        return input(prompt).strip()
    
    def get_num_choice_input(self, prompt: str, choice_map: Dict[str, str]) -> str:
        """通用的数字选项输入器，choice_map 是一个从数字字符串到选项描述的映射"""
        print(prompt)
        for key, value in (choice_map or {}).items():
            print(f"{key}: {value}")
        
        while True:
            user_input = input("请输入文本> ").strip()
            if user_input.isdigit() and user_input in choice_map:
                return choice_map[user_input]
            self.display_warning("无效输入，请输入有效的数字选项。")

    def get_num_choice_input_num(self, prompt: str, choice_map: Dict[str, str]) -> str:
        """通用的数字选项输入器，choice_map 是一个从数字字符串到选项描述的映射，但是返回用户输入的数字字符串，而不是映射后的值"""
        print(prompt)
        for key, value in (choice_map or {}).items():
            print(f"{key}: {value}")
        
        while True:
            user_input = input("请输入文本> ").strip()
            if user_input.isdigit() and user_input in choice_map:
                return user_input
            elif user_input.isdigit() == False and user_input in choice_map.values():
                # 允许用户直接输入选项描述来选择
                for key, value in choice_map.items():
                    if user_input.strip().lower() == value.strip().lower():
                        return key
                
            self.display_warning("无效输入，请输入有效的数字选项。")

    def get_model_choice(self) -> str:
        return self.get_num_choice_input("请选择模型：", self.model_map)
    
    def get_en_or_disable_or_auto_input(self, prompt: str) -> str:
        """获取启用/禁用/自动选项的输入，返回 'enabled'、'disabled' 或 'auto'"""
        options = {"1": "enabled", "2": "disabled", "3": "auto"}
        print(prompt)
        for key, value in options.items():
            print(f"{key}: {value}")
        
        while True:
            user_input = input("请输入文本> ").strip()
            if user_input in options:
                return options[user_input]
            self.display_warning("无效输入，请输入 1、2 或 3。")

    def _get_chat_result_image_dir(self) -> str:
        project_root = os.path.dirname(os.path.dirname(__file__))
        date_dir = datetime.now().strftime("%Y-%m-%d")
        image_dir = os.path.join(project_root, "chat_result", "imgs", date_dir)
        os.makedirs(image_dir, exist_ok=True)
        return image_dir

    def _generate_unique_image_name(self, extension: str = ".png") -> str:
        ext = (extension or ".png").lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        # 文件名无空格，并使用 UUID 保证唯一性
        return f"img_{uuid.uuid4().hex}{ext}"

    def _hash_file(self, file_path: str) -> str:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _build_image_hash_index(self, image_dir: str, valid_extensions: Tuple[str, ...]) -> Dict[str, str]:
        hash_index: Dict[str, str] = {}
        if not os.path.isdir(image_dir):
            return hash_index

        for name in os.listdir(image_dir):
            file_path = os.path.join(image_dir, name)
            if not os.path.isfile(file_path):
                continue
            if not name.lower().endswith(valid_extensions):
                continue
            try:
                file_hash = self._hash_file(file_path)
                hash_index[file_hash] = file_path
            except Exception:
                # 单个文件异常不影响整体流程
                continue
        return hash_index

    def _save_image_with_dedup(
        self,
        source_path: str,
        image_dir: str,
        valid_extensions: Tuple[str, ...],
        hash_index: Dict[str, str]
    ) -> str:
        file_hash = self._hash_file(source_path)
        existing_path = hash_index.get(file_hash)
        if existing_path:
            return existing_path
        
        _, ext = os.path.splitext(source_path)
        ext = ext.lower() if ext and ext.lower() in valid_extensions else ".png"
        target_path = os.path.join(image_dir, self._generate_unique_image_name(ext))
        shutil.copy2(source_path, target_path)
        saved_path = target_path
        hash_index[file_hash] = saved_path
        return saved_path

    def _save_clipboard_image_with_dedup(self, image_obj: Image.Image, image_dir: str, hash_index: Dict[str, str]) -> str:
        buffer = io.BytesIO()
        image_obj.save(buffer, format="PNG")
        image_hash = hashlib.sha256(buffer.getvalue()).hexdigest()
        existing_path = hash_index.get(image_hash)
        if existing_path:
            return existing_path

        target_path = os.path.join(image_dir, self._generate_unique_image_name(".png"))
        image_obj.save(target_path)
        hash_index[image_hash] = target_path
        return target_path
    
    def get_image_input(self, model_name: str) -> List[str]:
        is_image = input("是否输入图片[y/N]：").strip().lower() == 'y'
        if not is_image:
            return []
        path_list = []
        image_dir = self._get_chat_result_image_dir()
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')
        hash_index = self._build_image_hash_index(image_dir, valid_extensions)

        def append_unique_path(target_path: str):
            if target_path in path_list:
                return
            path_list.append(target_path)

        if "gemini" in model_name or "doubao" in model_name or "qwen" in model_name or "deepseek" in model_name:
            clipboard_content = ImageGrab.grabclipboard()
            if clipboard_content is not None:
                if isinstance(clipboard_content, Image.Image):
                    use_clipboard_img = self.get_boolean_input("检测到剪贴板中有图片，是否使用剪贴板图片？", True)
                    if use_clipboard_img:
                        target_path = self._save_clipboard_image_with_dedup(clipboard_content, image_dir, hash_index)
                        append_unique_path(target_path)
                elif isinstance(clipboard_content, list):
                    clipboard_files = []
                    for file_path in clipboard_content:
                        if os.path.isfile(file_path) and file_path.lower().endswith(valid_extensions):
                            clipboard_files.append(file_path)
                    use_clipboard_img = self.get_boolean_input("检测到剪贴板中有图片，是否使用剪贴板图片？", True)
                    if use_clipboard_img:
                        for file_path in clipboard_files:
                            saved_path = self._save_image_with_dedup(file_path, image_dir, valid_extensions, hash_index)
                            append_unique_path(saved_path)

            # 本地文件
            image_path = input("请输入图片本地文件路径(多个用逗号分隔)：").replace('"', '').replace("'", "")
            raw_paths = [p.strip() for p in image_path.replace('，', ',').split(',') if p.strip()]
            for p in raw_paths:
                if os.path.exists(p):
                    if os.path.isfile(p) and p.lower().endswith(valid_extensions):
                        saved_path = self._save_image_with_dedup(p, image_dir, valid_extensions, hash_index)
                        append_unique_path(saved_path)
                    else:
                        self.display_warning(f"图片格式不支持或路径不是文件：{p}")
                else:
                    self.display_warning(f"无法读取图片文件：{p}，请检查路径。")
        else:
            self.display_warning(f"当前模型 {model_name} 暂不支持图片输入。")
            path_list = []
            
        return path_list
    
    def get_text_file_input(self) -> str:
        file_path = input("请输入文件路径：").replace('"', '').replace("'", "").strip()
        if not os.path.exists(file_path):
            self.display_warning("文件不存在。")
            return ""
        try:
            return DocumentParser().parse(file_path)
        except UnsupportedFileFormatError as e:
            self.display_warning(str(e))
            return self.get_text_file_input()


    def get_boolean_input(self, prompt: str, default: bool = False) -> bool:
        """通用的 Yes/No 询问器"""
        reminder = "[Y/n]" if default else "[y/N]"
        while True:
            user_input = input(f"{prompt}{reminder}: ").strip().lower()
            if user_input == "":
                return default
            if user_input in {"y", "yes"}:
                return True
            if user_input in {"n", "no"}:
                return False
            self.display_warning("请输入 y/yes 或 n/no。")
    
    def render_stream(self, stream: Generator[Dict[str, Any], None, None]) -> Tuple[str, str, Dict]:
        """
        消费底层 LLM 传来的流式数据，负责优雅地打印到终端。
        返回 (最终答案, 思考过程, 元数据字典)
        """
        self.display_system(msg="已收到 AI 回执，正在生成回答\n", is_flush=True)
        
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

            elif chunk_type == "input":
                final_answer = self.get_user_input(prompt="请自己回答：")
            
            elif chunk_type == "error_msg":
                final_answer = self.get_user_input(prompt="请输入错误消息：")

        print("\n", end="") # 流结束换行
        
        # 补充打印耗时信息
        thinking_time = meta_info.get("thinking_time", -1.0)
        if thinking_time > 0:
            print(f"\033[90m(思考耗时: {thinking_time:.2f}秒)\033[0m")
            
        return final_answer, thought_content, meta_info
    
    def display_warning(self, msg: str):
        """标准化的警告输出（黄色）"""
        if msg.startswith("\n"):
            print(f"\033[93m[W] {msg}\033[0m", end="")
        print(f"\n\033[93m[W] {msg}\033[0m")

    def display_error(self, msg: str):
        """标准化的错误输出（红色）"""
        if msg.startswith("\n"):
            print(f"\033[91m[E] {msg}\033[0m", end="")
        print(f"\n\033[91m[E] {msg}\033[0m")

    def display_system(self, msg: str, is_flush: bool = False):
        """标准化的系统提示（蓝色）"""
        if msg.startswith("\n"):
            print(f"\033[94m[S] {msg}\033[0m", end="", flush=is_flush)
        print(f"\n\033[94m[S] {msg}\033[0m", flush=is_flush)

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