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

try:
    from prompt_toolkit import prompt as toolkit_prompt
    from prompt_toolkit.completion import PathCompleter, WordCompleter, NestedCompleter
except ImportError:
    toolkit_prompt = None
    PathCompleter = None
    WordCompleter = None
    NestedCompleter = None

class UIController:
    def __init__(self):
        self._spinner_registry = []
        self.chat_commands = {
            "/quit": "退出当前对话",
            "/format": "从本地文件读取文本作为输入",
            "/autoask": "自动生成提问内容",
            "/model": "切换当前模型",
            "/fork": "从历史轮次 fork 对话",
            "/quit_without_saving": "退出且不保存当前会话",
        }
        self.model_map = {
            "0": "自己回答",
            "1": "deepseek-agent-preview",
            "2": "deepseek-v4-flash",
            "3": "deepseek-v4-pro",
            "4": "multi-assistant-old-preview",
            "5": "错误消息",
            "6": "math-model",
            "7": "gemini-3.1-flash-lite-preview",
            "8": "gemini-3-flash-preview",
            "9": "gemini-3.1-pro-preview",
            "10": "qwen3.5-plus",
            "11": "qwen3.6-plus",
            "12": "doubao-seed-2-0-pro-260215",
            "13": "doubao-seed-2-0-lite-260215",
            "14": "doubao-seed-2-0-mini-260215",
            "15": "doubao-seed-1-8-251228",
            "16": "doubao-seed-1-6-251015",
            "17": "doubao-seed-1-6-flash-250828",
            "18": "kimi-k2.5",
            "19": "MiniMax-M2.7",
            "20": "MiniMax-M2.5",
            "21": "doubao-seedream-5-0-260128",
            "22": "doubao-seedream-4-5-251128"
            }

    def get_user_input(self, prompt: str = "请输入文本：", empty_choice: str = None) -> str:
        if empty_choice is not None:
            return empty_choice if prompt.strip() == "" else self._read_input(prompt)
        return self._read_input(prompt)

    def get_chat_input(self, prompt: str = "请输入文本", current_model: str = "") -> Dict[str, str]:
        """获取支持 / 命令的聊天输入。"""
        prompt_prefix = f"[{current_model}] " if current_model else ""
        input_prompt = f"{prompt_prefix}{prompt}> "
        if NestedCompleter:
            command_completer = NestedCompleter.from_nested_dict({
                "/quit": None,
                "/format": None,
                "/autoask": None,
                "/model": {value: None for value in self.model_map.values()},
                "/fork": None,
                "/system": None,
                "/quit_without_saving": None,
            })
        else:
            command_completer = WordCompleter(list(self.chat_commands.keys()), ignore_case=True) if WordCompleter else None

        while True:
            raw_input = self._read_input(input_prompt, completer=command_completer)
            if not raw_input:
                return {"kind": "text", "text": "", "command": "", "argument": ""}

            normalized = raw_input.strip()
            command_name, command_argument = self._split_command(normalized)

            if command_name in {"quit", "q", "exit"}:
                return {"kind": "command", "text": "", "command": "quit", "argument": command_argument}

            if command_name == "format":
                file_path = command_argument or self._prompt_file_path("请输入文件路径：")
                if not file_path:
                    self.display_warning("未提供文件路径，请重新输入。")
                    continue
                file_text = self._read_plain_text_file(file_path)
                if file_text == "":
                    continue
                return {"kind": "command", "text": file_text, "command": "format", "argument": file_path}

            if command_name == "autoask":
                return {"kind": "command", "text": "", "command": "autoask", "argument": command_argument}
            
            if command_name == "system":
                new_system_prompt = command_argument.strip()
                if not new_system_prompt:
                    self.display_warning("系统提示不能为空，请重新输入。")
                    continue
                return {"kind": "command", "text": new_system_prompt, "command": "system", "argument": ""}
            
            if command_name == "fork":
                if command_argument and command_argument.isdigit():
                    if int(command_argument) < 1:
                        self.display_warning("轮次必须是大于等于 1 的整数。")
                        command_argument = ""
                        continue
                    return {"kind": "command", "text": "", "command": "fork", "argument": command_argument}
                else:
                    fork_epoch = self.get_num_input(prompt="请输入要 fork 的对话轮次")
                    if fork_epoch < 1:
                        self.display_warning("轮次必须是大于等于 1 的整数。")
                        continue
                    return {"kind": "command", "text": "", "command": "fork", "argument": str(fork_epoch)}
                
            if command_name == "quit_without_saving":
                quit = self.get_boolean_input("确定要退出且不保存当前会话吗？", False)
                return {"kind": "command", "text": "", "command": "quit_without_saving", "argument": ""} if quit else {"kind": "text", "text": "", "command": "quit", "argument": ""}

            if command_name == "model":
                model_name = command_argument.strip()
                if not model_name:
                    self.display_system("当前可用模型：")
                    for key, value in self.model_map.items():
                        print(f"{key}: {value}")
                    continue
                return {"kind": "command", "text": "", "command": "model", "argument": model_name}

            if normalized.startswith("/"):
                self.display_warning("未知命令。可用命令：/quit、/format、/autoask、/model、/fork、/quit_without_saving")
                continue

            if normalized.lower() in {"q", "quit", "exit"}:
                return {"kind": "command", "text": "", "command": "quit", "argument": ""}
            if normalized.lower() == "format":
                file_path = self._prompt_file_path("请输入文件路径：")
                file_text = self._read_plain_text_file(file_path)
                if file_text == "":
                    continue
                return {"kind": "command", "text": file_text, "command": "format", "argument": file_path}
            if normalized.lower() == "autoask":
                return {"kind": "command", "text": "", "command": "autoask", "argument": ""}

            return {"kind": "text", "text": normalized, "command": "", "argument": ""}

    def _read_input(self, prompt: str, completer=None) -> str:
        if toolkit_prompt is not None:
            try:
                return toolkit_prompt(prompt, completer=completer, complete_while_typing=True).strip()
            except EOFError:
                return ""
        return input(prompt).strip()

    def _split_command(self, raw_input: str) -> Tuple[str, str]:
        if not raw_input.startswith("/"):
            return "", ""
        command_body = raw_input[1:].strip()
        if not command_body:
            return "", ""
        parts = command_body.split(maxsplit=1)
        command_name = parts[0].lower()
        command_argument = parts[1].strip() if len(parts) > 1 else ""
        return command_name, command_argument

    def _prompt_file_path(self, prompt: str) -> str:
        path_completer = PathCompleter(expanduser=True) if PathCompleter else None
        while True:
            file_path = self._read_input(prompt, completer=path_completer).replace('"', '').replace("'", "").strip()
            if file_path:
                return file_path
            self.display_warning("文件路径不能为空。")

    def _read_plain_text_file(self, file_path: str) -> str:
        normalized_path = file_path.replace('"', '').replace("'", "").strip()
        if not os.path.exists(normalized_path):
            self.display_warning("文件不存在。")
            return ""
        try:
            with open(normalized_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            self.display_warning(f"读取文件失败 {normalized_path}: {e}")
            return ""
    
    def get_num_choice_input(self, prompt: str, choice_map: Dict[str, str], default_num_choice: str = None) -> str:
        """通用的数字选项输入器，choice_map 是一个从数字字符串到选项描述的映射
        default_num_choice 是默认选项对应的数字字符串，如果用户直接回车则选择默认选项"""
        print(prompt)
        for key, value in (choice_map or {}).items():
            print(f"{key}: {value}")

        while True:
            user_input = input("请输入文本> ").strip()
            if user_input.isdigit() and user_input in choice_map:
                return choice_map[user_input]
            elif default_num_choice is not None and (user_input == "" or user_input is None):
                return default_num_choice
            self.display_warning("无效输入，请输入有效的数字选项。")

    def get_num_choice_input_num(self, prompt: str, choice_map: Dict[str, str], default_num_choice: str = None) -> str:
        """通用的数字选项输入器，choice_map 是一个从数字字符串到选项描述的映射，但是返回用户输入的数字字符串，而不是映射后的值
        default_num_choice 是默认选项对应的数字字符串，如果用户直接回车则选择默认选项"""
        print(prompt)
        for key, value in (choice_map or {}).items():
            print(f"{key}: {value}")
        
        while True:
            user_input = input("请输入文本> ").strip()
            if user_input.isdigit() and user_input in choice_map:
                return user_input
            elif default_num_choice is not None and (user_input == "" or user_input is None):
                return default_num_choice
            elif user_input.isdigit() == False and user_input in choice_map.values():
                # 允许用户直接输入选项描述来选择
                for key, value in choice_map.items():
                    if user_input.strip().lower() == value.strip().lower():
                        return key
                
            self.display_warning("无效输入，请输入有效的数字选项。")

    def get_model_choice(self) -> str:
        return self.get_num_choice_input("请选择模型：", self.model_map)

    def resolve_model_name(self, model_name: str) -> str:
        normalized = (model_name or "").strip()
        if not normalized:
            return ""

        if normalized in self.model_map:
            return self.model_map[normalized]

        for key, value in self.model_map.items():
            if normalized.lower() == value.lower():
                return value

        alias_map = {
            "deepseek-chat": "deepseek-chat",
            "deepseek-reasoner": "deepseek-reasoner",
            "deepseek": "deepseek",
        }
        lowered = normalized.lower()
        if lowered in alias_map:
            return alias_map[lowered]

        return normalized
    
    def get_num_input(self, prompt: str = "请输入文本", default: int = None) -> int:
        """获取数字输入，支持默认值"""
        while True:
            user_input = input(f"{prompt} {'[默认: ' + str(default) + ']' if default is not None else ''}> ").strip()
            if user_input.isdigit():
                try:
                    return int(user_input)
                except ValueError:
                    pass
            elif default is not None and user_input == "":
                return default
            self.display_warning("无效输入，请输入数字。")
    
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

        if "gemini" in model_name or "doubao" in model_name or "qwen" in model_name or "deepseek" in model_name or "kimi" in model_name:
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

    def _print_typewriter(self, text: str, color_code: str = "", base_delay: float = 0.008):
        """将完整字符串按 token 风格分块输出，模拟流式打印效果。"""
        if text is None:
            text = ""

        text_length = len(text)
        if text_length > 400:
            chunk_delay = 0.018
        elif text_length > 200:
            chunk_delay = 0.022
        else:
            chunk_delay = max(base_delay * 2.5, 0.014)

        if color_code:
            print(color_code, end="", flush=True)

        idx = 0
        while idx < text_length:
            remain = text_length - idx

            # 模拟 token 批量输出：一般每次输出 2~8 个字符，剩余较少时一次输出完。
            if remain <= 4:
                step = remain
            elif remain <= 12:
                step = 3
            elif remain <= 24:
                step = 4
            elif remain <= 80:
                step = 5
            else:
                step = 6

            chunk = text[idx:idx + step]
            print(chunk, end="", flush=True)
            idx += step

            # 如果这个分块尾部是标点，增加停顿，贴近真实阅读节奏。
            if chunk and chunk[-1] in "，。！？,.!?；;：:\n":
                time.sleep(chunk_delay * 1.8)
            else:
                time.sleep(chunk_delay)

        if color_code:
            print("\033[0m", end="", flush=True)
        print()
    
    def _render_stream_legacy(self, stream: Generator[Dict[str, Any], None, None]) -> Tuple[str, str, Dict]:
        """
        消费底层 LLM 传来的流式数据，负责优雅地打印到终端。
        返回 (最终答案, 思考过程, 元数据字典)
        """
        final_answer = ""
        thought_content = ""
        meta_info = {}
        is_thinking = False
        is_first_content = True
        meta_info = {"ocr_results": []} # 专门开辟一个列表放 OCR 记录

        for chunk in stream:
            if not isinstance(chunk, dict):
                continue
            chunk_type = chunk.get("type")
            content = chunk.get("content", "")
            content_dict = chunk.get("content_dict", {})

            if chunk_type == "meta_ocr":
                # 将 OCR 结果暂存在 meta 中
                meta_info["ocr_results"].append({
                    "image_path": chunk["image_path"], 
                    "ocr_text": chunk["ocr_text"]
                })

            elif chunk_type == "thinking":
                is_thinking = True
                if chunk.get("display", True):
                    print(f"\033[90m{content}\033[0m", end="", flush=True)
                thought_content += content

            elif chunk_type == "content":
                # 如果刚才还在思考，现在开始输出正文了，打印一条绿色分割线
                if is_thinking and is_first_content:
                    # 这里的耗时会在流结束后通过 meta 传来，但为了体验，可以在这里打印分割线
                    print(f"\n\n\033[92m思考结束，开始回答...\033[0m\n", end="")
                    is_thinking = False
                    is_first_content = False
                    
                print(content, end="", flush=True)
                final_answer += content

            elif chunk_type == "meta":
                meta_info.update(chunk)

            elif chunk_type == "system":
                # 打印系统级别的提示（比如上传图片的进度）
                print(f"\033[94m[S] {content}\033[0m", end="", flush=True)
            
            elif chunk_type == "abstract":
                title = content_dict.get("title", "")
                abstract = content_dict.get("abstract", "")
                self._print_typewriter(title, color_code="\033[97m")
                self._print_typewriter(abstract, color_code="\033[90m")

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
    
    def render_stream(self, stream: Generator[Dict[str, Any], None, None]) -> Tuple[str, str, Dict]:
        final_answer = ""
        thought_content = ""
        meta_info = {
            "ocr_results": [],
            "thinking_times": [],
        }
        is_thinking = False
        pending_thinking_boundary = False
        pending_thinking_time = None
        last_output_ended_with_newline = True

        def _append_unique_meta_items(key: str, values: Any) -> None:
            if values is None:
                return
            if not isinstance(values, list):
                values = [values]
            target = meta_info.setdefault(key, [])
            for value in values:
                if value not in target:
                    target.append(value)

        def _mark_output_tail(text: str) -> None:
            nonlocal last_output_ended_with_newline
            last_output_ended_with_newline = str(text).endswith("\n")

        def _ensure_line_break() -> None:
            nonlocal last_output_ended_with_newline
            if not last_output_ended_with_newline:
                print()
                last_output_ended_with_newline = True

        def _flush_thinking_footer(show_transition: bool) -> None:
            nonlocal is_thinking, pending_thinking_boundary, pending_thinking_time, last_output_ended_with_newline
            if not pending_thinking_boundary:
                return
            _ensure_line_break()
            if pending_thinking_time is not None and pending_thinking_time > 0:
                print(f"\033[90m(思考耗时: {pending_thinking_time:.2f}秒)\033[0m")
                meta_info["thinking_time"] = pending_thinking_time
                last_output_ended_with_newline = True
            if show_transition:
                print("\033[92m思考结束，开始输出...\033[0m")
                last_output_ended_with_newline = True
            is_thinking = False
            pending_thinking_boundary = False
            pending_thinking_time = None

        for chunk in stream:
            if not isinstance(chunk, dict):
                continue

            chunk_type = chunk.get("type")
            content = chunk.get("content", "")
            content_dict = chunk.get("content_dict", {})

            if chunk_type == "meta_ocr":
                meta_info["ocr_results"].append({
                    "image_path": chunk["image_path"],
                    "ocr_text": chunk["ocr_text"]
                })
            elif chunk_type == "image_placeholder":
                _flush_thinking_footer(show_transition=False)
                _ensure_line_break()
                try:
                    placeholder_count = int(chunk.get("count", 1) or 1)
                except (TypeError, ValueError):
                    placeholder_count = 1
                print(f"\033[94m[S] 正在生成图片，共 {placeholder_count} 张...\033[0m")
                last_output_ended_with_newline = True
            elif chunk_type == "image_generated":
                _flush_thinking_footer(show_transition=False)
                _ensure_line_break()
                image_path = str(chunk.get("image_path", "") or "")
                size_text = str(chunk.get("size", "") or "")
                try:
                    image_index = int(chunk.get("index", 0) or 0) + 1
                except (TypeError, ValueError):
                    image_index = 1
                suffix = f" ({size_text})" if size_text else ""
                print(f"\033[94m[S] 第 {image_index} 张图片已保存: {image_path}{suffix}\033[0m")
                last_output_ended_with_newline = True
            elif chunk_type == "image_failed":
                _flush_thinking_footer(show_transition=False)
                _ensure_line_break()
                try:
                    image_index = int(chunk.get("index", 0) or 0) + 1
                except (TypeError, ValueError):
                    image_index = 1
                error_text = str(chunk.get("error", "") or "图片保存失败")
                print(f"\033[93m[W] 第 {image_index} 张图片处理失败: {error_text}\033[0m")
                last_output_ended_with_newline = True
            elif chunk_type == "thinking":
                if not is_thinking:
                    _ensure_line_break()
                is_thinking = True
                pending_thinking_boundary = True
                if chunk.get("display", True):
                    print(f"\033[90m{content}\033[0m", end="", flush=True)
                    _mark_output_tail(content)
                thought_content += content
            elif chunk_type == "content":
                _flush_thinking_footer(show_transition=False)
                print(content, end="", flush=True)
                _mark_output_tail(content)
                final_answer += content
            elif chunk_type == "meta":
                thinking_time = chunk.get("thinking_time", None)
                if isinstance(thinking_time, (int, float)) and thinking_time > 0:
                    pending_thinking_time = float(thinking_time)
                    meta_info["thinking_time"] = float(thinking_time)
                    meta_info["thinking_times"].append(float(thinking_time))

                for list_key in ("uris", "search_keywords", "assistant_questions", "user_inputs", "tool_call_history", "generated_images", "image_failures"):
                    if list_key in chunk:
                        _append_unique_meta_items(list_key, chunk.get(list_key))

                for key, value in chunk.items():
                    if key in {"type", "thinking_time", "uris", "search_keywords", "assistant_questions", "user_inputs", "tool_call_history", "generated_images", "image_failures"}:
                        continue
                    meta_info[key] = value
            elif chunk_type == "system":
                _flush_thinking_footer(show_transition=False)
                _ensure_line_break()
                print(f"\033[94m[S] {content}\033[0m", end="", flush=True)
                _mark_output_tail(content)
            elif chunk_type == "abstract":
                _flush_thinking_footer(show_transition=False)
                title = content_dict.get("title", "")
                abstract = content_dict.get("abstract", "")
                self._print_typewriter(title, color_code="\033[97m")
                self._print_typewriter(abstract, color_code="\033[90m")
                last_output_ended_with_newline = True
            elif chunk_type == "input":
                _flush_thinking_footer(show_transition=False)
                final_answer = self.get_user_input(prompt="璇疯嚜宸卞洖绛旓細")
                last_output_ended_with_newline = True
            elif chunk_type == "error_msg":
                _flush_thinking_footer(show_transition=False)
                final_answer = self.get_user_input(prompt="璇疯緭鍏ラ敊璇秷鎭細")
                last_output_ended_with_newline = True

        _flush_thinking_footer(show_transition=False)
        if not last_output_ended_with_newline:
            print()

        return final_answer, thought_content, meta_info

    def display_warning(self, msg: str):
        """标准化的警告输出（黄色）"""
        if msg.startswith("\n"):
            print(f"\033[93m[W] {msg}\033[0m")
        print(f"\033[93m[W] {msg}\033[0m")

    def display_error(self, msg: str):
        """标准化的错误输出（红色）"""
        if msg.startswith("\n"):
            print(f"\033[91m[E] {msg}\033[0m")
        print(f"\033[91m[E] {msg}\033[0m")

    def display_system(self, msg: str, is_flush: bool = False):
        """标准化的系统提示（蓝色）"""
        if msg.startswith("\n"):
            print(f"\033[94m[S] {msg}\033[0m", end="" if is_flush else "\n", flush=is_flush)
        print(f"\033[94m[S] {msg}\033[0m", end="" if is_flush else "\n", flush=is_flush)

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
