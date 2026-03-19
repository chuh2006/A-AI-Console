from typing import Dict, Generator, List
import json
from openai import OpenAI
import time
from .llm_base import BaseLLMClient
from tools.vision_tools import ocr_tool_schema, perform_ocr

class OpenAICompatibleClient(BaseLLMClient):
    def chat_stream(self, messages: List[Dict[str, str | list]], temperature: float, image_paths: List[str] = None, **kwargs) -> Generator[Dict[str, str], None, None]:
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        
        # 1. 处理请求参数和特殊结构
        is_qwen = "qwen" in self.model_name
        is_qwen_thinking = kwargs.get("isQwenThinking", False)
        is_deepseek_chat = self.model_name == "deepseek-chat"
        
        # 深拷贝以防修改原始 Session 中的历史记录
        req_messages = [msg.copy() for msg in messages]
        tools = None
        
        # 处理 Qwen 的图片输入格式 (将最后一条消息的 content 转为 list)
        if is_qwen and image_paths:
            last_content = req_messages[-1]["content"]
            new_content = [{"type": "text", "text": last_content}]
            for img_url in image_paths:
                new_content.append({"type": "image_url", "image_url": {"url": img_url}})
            req_messages[-1]["content"] = new_content
        if "deepseek" in self.model_name and image_paths:
            paths_str = "、".join(image_paths)
            if is_deepseek_chat:
                # Chat 支持 Function Calling，交给大模型自主决定是否调 OCR
                req_messages[-1]["content"] += f"\n\n[系统提示：用户随附了本地图片，路径为：{paths_str}。如有必要，请调用 perform_ocr 工具读取其文字。]"
                tools = [ocr_tool_schema]
            else:
                # Reasoner 不支持 Function Calling，直接强制本地 OCR 帮它看
                ocr_results = [f"图片 {p} 提取文本：\n{perform_ocr(p)}" for p in image_paths]
                ocr_inject_str = "\n".join(ocr_results)
                req_messages[-1]["content"] += f"\n\n[系统提示：用户随附了图片，以下是系统自动为您提取的图片OCR文本：\n{ocr_inject_str}\n请结合以上信息回答用户。]"

                # 抛出元数据，好让 Session 去保存
                for p, txt in zip(image_paths, ocr_results):
                    yield {"type": "meta_ocr", "image_path": p, "ocr_text": txt}

        extra_body = {"enable_thinking": is_qwen_thinking} if is_qwen and is_qwen_thinking else None

        def run_api(msgs, active_tools):
            return client.chat.completions.create(
                model=self.model_name,
                messages=msgs,
                temperature=temperature,
                stream=True,
                tools=active_tools,
                extra_body=extra_body
            )

        # 2. 发起流式请求
        stream = client.chat.completions.create(
            model=self.model_name,
            messages=req_messages,
            temperature=temperature,
            stream=True,
            extra_body=extra_body,
            tools=tools if tools else None
        )
        tool_calls_buffer = {}
        begin_time = time.time() if "reasoner" in self.model_name or is_qwen_thinking else None
        
        # ====================================================
        # 第一轮流式处理 (带 Tool Call 截获)
        # ====================================================
        tool_calls_buffer = {}
        isThinkingTime = False
        for chunk in stream:
            if not chunk.choices: continue
            delta = chunk.choices[0].delta
            
            # 捕获流式输出中的 function calls
            if getattr(delta, 'tool_calls', None):
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_buffer:
                        tool_calls_buffer[idx] = {
                            "id": tc.id, "type": "function", 
                            "function": {"name": tc.function.name or "", "arguments": tc.function.arguments or ""}
                        }
                    else:
                        if tc.function.name: tool_calls_buffer[idx]["function"]["name"] += tc.function.name
                        if tc.function.arguments: tool_calls_buffer[idx]["function"]["arguments"] += tc.function.arguments
            elif getattr(delta, 'content', None):
                if isThinkingTime:
                    yield {"type": "meta", "thinking_time": time.time() - begin_time}
                    isThinkingTime = False
                yield {"type": "content", "content": delta.content}
            elif getattr(delta, 'reasoning_content', None):
                isThinkingTime = True
                yield {"type": "thinking", "content": delta.reasoning_content}

        # ====================================================
        # 处理被触发的工具，并进行第二轮请求
        # ====================================================
        if tool_calls_buffer:
            tool_calls_list = list(tool_calls_buffer.values())
            # 1. 必须先把 assistant 的 tool_calls 挂载到历史中
            req_messages.append({"role": "assistant", "content": "", "tool_calls": tool_calls_list})

            # 2. 执行工具
            for tc in tool_calls_list:
                if tc["function"]["name"] == "perform_ocr":
                    try:
                        args = json.loads(tc["function"]["arguments"])
                        target_path = args.get("image_path", "")
                    except json.JSONDecodeError:
                        target_path = ""
                    
                    yield {"type": "system", "content": f"\n\033[94m[DeepSeek 请求工具] 正在提取图片文本: {target_path}...\033[0m\n"}
                    ocr_result = perform_ocr(target_path)
                    yield {"type": "system", "content": f"\033[93m[本地OCR返回给模型的结果]: {ocr_result}\033[0m\n"}
                    # 发送回传，通知 UI 和 Session 存留证据
                    yield {"type": "meta_ocr", "image_path": target_path, "ocr_text": ocr_result}

                    # 将执行结果作为 tool 角色追加
                    req_messages.append({"role": "tool", "tool_call_id": tc["id"], "content": ocr_result})

            # 3. 带上工具的提取结果，进行第二轮问答
            isThinkingTime = False
            second_stream = run_api(req_messages, None)
            for chunk in second_stream:
                if not chunk.choices: continue
                delta = chunk.choices[0].delta
                if getattr(delta, 'content', None):
                    if isThinkingTime:
                        yield {"type": "meta", "thinking_time": time.time() - begin_time}
                        isThinkingTime = False
                    yield {"type": "content", "content": delta.content}
                elif getattr(delta, 'reasoning_content', None):
                    isThinkingTime = True
                    yield {"type": "thinking", "content": delta.reasoning_content}

        client.close()