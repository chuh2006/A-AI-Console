from typing import Dict, Generator, List
import json
from openai import OpenAI
import time
import os
import base64
from .llm_base import BaseLLMClient
from tools.vision_tools import ocr_tool_schema, perform_ocr
from tools.web_search_ds import web_search_tool_schema, search_web
from tools.prompts import Prompts
from tools.kimi_tools import kimi_web_search_tool_schema, search_impl
from tools.time_get import time_tool_schema, get_time
from tools.make_new_function_tool import create_new_tool_schema, create_new_tool  # 暂时弃用
from tools.run_new_function import run_func
from tools.get_user import get_user_schema, get_user
from tools.think_abstract import think_abstract_schema, think_abstract

class OpenAICompatibleClient(BaseLLMClient):
    def sanitize_tool_call_messages(self, raw_messages: List[Dict]) -> List[Dict]:
        """清理不符合 tool-calling 协议的历史消息，避免 400 invalid_request_error。"""
        cleaned: List[Dict] = []
        idx = 0
        while idx < len(raw_messages):
            msg = raw_messages[idx]
            role = msg.get("role")
            if role == "assistant" and msg.get("tool_calls"):
                expected_ids = {
                    tc.get("id")
                    for tc in msg.get("tool_calls", [])
                    if isinstance(tc, dict) and tc.get("id")
                }
                # assistant 标记了 tool_calls，但没有有效 id 时，降级为普通 assistant 消息
                if not expected_ids:
                    assistant_msg = msg.copy()
                    assistant_msg.pop("tool_calls", None)
                    cleaned.append(assistant_msg)
                    idx += 1
                    continue
                found_ids = set()
                collected_tool_msgs: List[Dict] = []
                probe = idx + 1
                # tool 消息必须紧跟在 assistant(tool_calls) 后面
                while probe < len(raw_messages) and raw_messages[probe].get("role") == "tool":
                    tool_msg = raw_messages[probe]
                    tool_call_id = tool_msg.get("tool_call_id")
                    if tool_call_id in expected_ids and tool_call_id not in found_ids:
                        collected_tool_msgs.append(tool_msg)
                        found_ids.add(tool_call_id)
                    probe += 1
                if found_ids == expected_ids:
                    cleaned.append(msg)
                    cleaned.extend(collected_tool_msgs)
                else:
                    # 不完整的 tool-calls 轮次会导致后续请求报错，这里降级为普通 assistant 内容
                    assistant_msg = msg.copy()
                    assistant_msg.pop("tool_calls", None)
                    cleaned.append(assistant_msg)
                idx = probe
                continue
            if role == "tool":
                # 孤立 tool 消息直接丢弃
                idx += 1
                continue
            cleaned.append(msg)
            idx += 1
        return cleaned

    def chat_stream(self, messages: List[Dict[str, str | list]], temperature: float, image_paths: List[str] = None, **kwargs) -> Generator[Dict[str, str], None, None]:
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        using_kimi = "kimi" in self.model_name
        using_deepseek_reasoner = "reasoner" in self.model_name
        using_deepseek = "deepseek" in self.model_name
        using_deepseek_agent = kwargs.get("enable_agent", False) and using_deepseek

        # 深拷贝以防修改原始 Session 中的历史记录
        req_messages = [msg.copy() for msg in messages]
        tools = []
        extra_body = {}
        new_tool_names = []  # 用于存储本轮对话中动态创建的新工具的 name
        new_tool_schema = None
        new_tool_function = None
        get_user_questions = []  # 用于存储 get_user 工具调用中向用户提出的问题，以便后续分析和调试
        get_user_inputs = []  # 用于存储 get_user 工具调用中用户的输入，以便后续分析和调试
        tool_call_history: List[Dict] = []  # 用于记录所有工具调用的历史，包括工具名称、参数和返回结果，以便后续分析和调试

        # test:
        if using_deepseek_agent:
        # tools.append(create_new_tool_schema) if using_deepseek_agent else None
            tools.append(think_abstract_schema)
            # 在最前面加系统提示词
            req_messages.insert(0, {"role": "system", "content": Prompts.deepseek_agent_system})

        # 统一处理：让模型自主决定是否调用 OCR
        if using_deepseek:
            if image_paths:
                paths_str = "、".join(image_paths)
                req_messages[-1]["content"] += f"\n\n[系统提示：用户随附了本地图片，路径为：{paths_str}。如有必要，请调用 perform_ocr 工具读取其文字。]"
                tools.append(ocr_tool_schema)
            if kwargs.get("enable_enhanced_thinking", False):
                tools.append(get_user_schema)

        if using_kimi:
            if "kimi-k2.5" in self.model_name:
                temperature = None  # Kimi-K2.5 固定温度，强制关闭采样
            elif temperature >= 1.0:
                temperature = 1.0  # Kimi 温度上限为 1.0
            if kwargs.get("enable_thinking", False):
                pass # Kimi 默认开启思考功能，无需额外配置
            elif not kwargs.get("enable_thinking", True): # 用户显式要求关闭思考功能
                extra_body.update({"thinking": {"type": "disabled"}})
            if image_paths:
                last_msg = req_messages[-1]["content"]
                new_msg = [{"type": "text", "text": last_msg}]
                for path in image_paths:
                    with open(path, "rb") as f:
                        image_data = f.read()
                    img_url = f"data:image/{os.path.splitext(path)[1]};base64,{base64.b64encode(image_data).decode('utf-8')}"
                    new_msg.append({"type": "image_url", "image_url": {"url": img_url}})
                req_messages[-1]["content"] = new_msg

        max_iterations = 1 if tools else 0 # 默认不启用工具循环，除非至少有一个工具被添加

        kimi_thinking_enabled = using_kimi and kwargs.get("enable_thinking", False)

        # 添加网络搜索工具
        if kwargs.get("enable_search", False):
            if using_deepseek:
                max_iterations_str = kwargs.get("searchEffort", "low")
                tools.append(web_search_tool_schema) if max_iterations_str != "time_only" else None
                tools.append(time_tool_schema)
                reasoning_effort_map = {"minimal": 1, "low": 2, "medium": 4, "high": 5, "max": 8, "unlimited": 10, "time_only": 10} # time_only不给搜索工具，后面的数字无意义。
                max_iterations = reasoning_effort_map.get(max_iterations_str, 2)
            elif using_kimi:
                # 使用接口自带的搜索工具
                tools.append(kimi_web_search_tool_schema)
                max_iterations = 5
            else:
                pass

        if using_deepseek_agent:
            max_iterations += 10  # DeepSeek Agent 允许更多轮次的工具调用

        loop_count = 0
        get_user_count = 0
        status = -1 # -1: 初始状态，0: 思考，1: 正式回答
        begin_time = time.time() if using_deepseek_reasoner or using_kimi or using_deepseek_agent else None

        # ====================================================
        # 进入多轮 Tool Calling 循环
        # ====================================================
        while True:
            loop_count += 1

            req_messages = self.sanitize_tool_call_messages(req_messages)

            if kimi_thinking_enabled:
                for msg in req_messages:
                    if msg.get("role") == "assistant" and msg.get("tool_calls") and "reasoning_content" not in msg:
                        msg["reasoning_content"] = "[empty reasoning]"

            # 发起流式请求
            stream = client.chat.completions.create(
                model=self.model_name,
                messages=req_messages,
                temperature=temperature,
                stream=True,
                extra_body=extra_body,
                tools=tools if tools else None
            )
            
            # 初始化当前轮次的缓存
            tool_calls_buffer = {}
            reasoning_buffer = ""  
            content_buffer = ""    
            isThinkingTime = False
            finish_reason = None
            
            # 解析流式数据
            for chunk in stream:
                if not chunk.choices: continue
                delta = chunk.choices[0].delta
                
                # 捕获 function calls
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

                # 捕获思维链内容（注意：可能与 tool_calls 同时出现，不能用 elif）
                if getattr(delta, 'reasoning_content', None):
                    status = 0
                    reasoning_buffer += delta.reasoning_content
                    isThinkingTime = True
                    if not using_deepseek_agent:
                        yield {"type": "thinking", "content": delta.reasoning_content}
                    else:
                        yield {"type": "thinking", "content": delta.reasoning_content, "display": False}

                # 捕获常规回复内容
                if getattr(delta, 'content', None):
                    status = 1
                    content_buffer += delta.content
                    if isThinkingTime:
                        yield {"type": "meta", "thinking_time": time.time() - begin_time}
                        isThinkingTime = False
                    yield {"type": "content", "content": delta.content}

            # ====================================================
            # 检查当前轮次是否触发了工具
            # ====================================================
            if tool_calls_buffer:
                tool_calls_list = list(tool_calls_buffer.values())
                
                # 构建 assistant 消息并注入历史记录 (必须带上思维链)
                assistant_msg = {
                    "role": "assistant", 
                    "content": content_buffer, 
                    "tool_calls": tool_calls_list
                }
                if reasoning_buffer:
                    assistant_msg["reasoning_content"] = reasoning_buffer
                elif kimi_thinking_enabled:
                    # Kimi 在开启 thinking 且发生 tool call 时，要求 assistant 消息显式带 reasoning_content 字段
                    assistant_msg["reasoning_content"] = "[empty reasoning]"
                    
                req_messages.append(assistant_msg)

                # 执行工具
                for tc in tool_calls_list:
                    if loop_count > max_iterations and tc["function"]["name"] != "get_time":
                        tc["function"]["name"] = "max_tool_calls_exceeded"
                    if tc["function"]["name"] == "perform_ocr":
                        tool_status = "success"
                        try:
                            args = json.loads(tc["function"]["arguments"])
                            target_path = args.get("image_path", "")
                        except json.JSONDecodeError:
                            target_path = ""
                        
                        yield {"type": "system", "content": f"\033[94m[第 {loop_count} 轮 | 请求工具] 正在提取图片文本: {target_path}...\033[0m\n"} if not using_deepseek_agent else None
                        ocr_result = perform_ocr(target_path)
                        yield {"type": "system", "content": f"\033[93m[本地OCR返回结果]: {ocr_result[:50]}...\033[0m\n"} if not using_deepseek_agent else None
                        
                        yield {"type": "meta_ocr", "image_path": target_path, "ocr_text": ocr_result}

                        # 将执行结果作为 tool 角色追加
                        req_messages.append({
                            "role": "tool", 
                            "tool_call_id": tc["id"], 
                            "content": ocr_result
                        })
                        tool_call_history.append({
                            "name": tc["function"]["name"],
                            "status": "success"
                        })
                    elif tc["function"]["name"] == "search_web":
                        search_result = ""
                        try:
                            args = json.loads(tc["function"]["arguments"])
                            queries = args.get("queries", [])
                        except json.JSONDecodeError:
                            queries = []
                        if queries:
                            yield {"type": "system", "content": f"\033[94m[第 {loop_count} 轮 | 请求工具] 正在执行网络搜索，关键词: {queries}...\033[0m\n"} if not using_deepseek_agent else None
                            search_results = search_web(queries)
                            yield {"type": "meta", "search_keywords": queries, "uris": search_results.get("sources", [])}
                            yield {"type": "system", "content": f"\033[93m[网络搜索返回结果]: {search_results['results'][:50]}...\033[0m\n"} if not using_deepseek_agent else None
                        req_messages.append({
                            "role": "tool", 
                            "tool_call_id": tc["id"], 
                            "content": search_results['results']
                        })
                        tool_call_history.append({
                            "name": tc["function"]["name"],
                            "status": "success"
                        })
                    elif tc["function"]["name"] == "$web_search":  # Kimi 内置搜索工具
                        arguments = json.loads(tc["function"]["arguments"])
                        tool_result = search_impl(arguments)
                        yield {"type": "system", "content": f"\033[94m[第 {loop_count} 轮 | 请求工具] Kimi 内置搜索工具\033[0m\n"}
                        req_messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "name": tc["function"]["name"],
                            "content": json.dumps(tool_result["arguments"])
                        })
                        tool_call_history.append({
                            "name": tc["function"]["name"],
                            "status": "success"
                        })
                    elif tc["function"]["name"] == "get_time":
                        tool_result = get_time()
                        loop_count -= 1  # 时间工具不计入迭代次数限制
                        req_messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": tool_result
                        })
                        tool_call_history.append({
                            "name": tc["function"]["name"],
                            "status": "success",
                            "result": tool_result
                        })
                    elif tc["function"]["name"] == "get_user":
                        yield {"type": "system", "content": f"\033[94m[第 {loop_count} 轮 | 请求工具] 获取用户进一步输入\033[0m\n"} if not using_deepseek_agent else None
                        loop_count -= 1  # 获取用户输入不计入迭代次数限制
                        tool_status = "success"
                        if get_user_count >= 2:  # 限制最多向用户提出两次问题，防止过度依赖用户输入导致的死循环
                            req_messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": "Rejected: 已达到最大向用户提问次数限制，系统强制拦截所有 get_user 工具调用。请停止尝试获取用户输入"
                            })
                            tool_status = "rejected_max_count"
                        elif status == 1 and content_buffer.strip() != "":  # 如果已经有正式回答了，就不要再问用户了，防止模型在得到答案后又反过来质疑用户输入导致的死循环
                            req_messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": "Rejected: 正式回答过程中不允许调用 get_user 工具。请停止尝试获取用户输入"
                            })
                            tool_status = "rejected_no_thinking"
                        else:
                            question_str = tc["function"]["arguments"]
                            question_dict = json.loads(question_str)
                            question = question_dict.get("question", "请提供更多信息。")
                            input_type = question_dict.get("type", "提供信息")
                            missing_param = question_dict.get("missing_param", "相关信息")
                            options = question_dict.get("options", None)
                            user_response = get_user(question, input_type, missing_param, options)
                            get_user_questions.append(question_dict)  # 记录向用户提出的问题，以便后续分析
                            if user_response.get("result") == "success":
                                get_user_inputs.append(user_response["user_input"])  # 保存用户输入以供后续分析
                            else:
                                get_user_inputs.append(f"用户拒绝回答问题: {question}")  # 记录用户拒绝的情况
                                tool_status = "rejected_user_refusal"
                            req_messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": user_response.get("user_input", "")
                            })
                            tool_call_history.append({
                                "name": tc["function"]["name"],
                                "status": tool_status,
                            })
                            
                            get_user_count += 1  # 独立计数器

                    if tc["function"]["name"] == "think_abstract":
                        if status == 1 and content_buffer.strip() != "":
                            req_messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": "Rejected: 正式回答过程中不允许调用 think_abstract 工具。请停止尝试调用该工具"
                            })
                        ai_return_str = tc["function"]["arguments"]
                        ai_return_dict = think_abstract(ai_return_str)
                        yield {"type": "abstract", "content_dict": ai_return_dict}
                        loop_count -= 1  # think_abstract 工具不计入迭代次数限制
                        time.sleep(1)
                        req_messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": "Success: 成功调用工具并向用户展示了思考摘要，你可继续正常思考"
                        })


                    elif tc["function"]["name"] == "create_tool":
                        yield {"type": "system", "content": f"\033[94m[第 {loop_count} 轮 | 请求工具] 收到创建工具请求，名称: {tc['function']['arguments']}...\033[0m\n"}
                        args = json.loads(tc["function"]["arguments"])
                        name = args.get("name", "")
                        new_tool_names.append(name) if name else None
                        tool_result = create_new_tool(
                            api_key=self.api_key,
                            name=name,
                            description=args.get("description")
                        )
                        req_messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": tool_result.get("message", "创建工具失败")
                        })
                        if tool_result.get("result") == "success":
                            # 将新工具加入可用工具列表，供后续轮次调用
                            new_tool_schema = tool_result.get("schema")
                            new_tool_function = tool_result.get("function")
                            if new_tool_schema:
                                tools.append(new_tool_schema)
                                yield {"type": "system", "content": f"\033[92m工具 '{name}' 创建成功并已加入工具列表。\033[0m\n"}
                            else:
                                yield {"type": "system", "content": f"\033[91m工具 '{name}' 创建成功但未返回有效 schema，无法加入工具列表。\033[0m\n"}
                                req_messages[-1]["content"] += " (注意：未返回有效 schema，无法加入工具列表，你不能调用该工具)"
                            
                    
                    elif tc["function"]["name"] in new_tool_names:
                        yield {"type": "system", "content": f"\033[94m[第 {loop_count} 轮 | 请求工具] 正在执行新创建的工具 '{tc['function']['name']}'...\033[0m\n"}
                        args = json.loads(tc["function"]["arguments"])
                        vars = []
                        for k, v in args.items():
                            vars.append({"name": k, "value": v})

                        result = run_func(function_name = tc["function"]["name"], function_source = new_tool_function, variables = vars)
                        if result.get("ok", False) == True:
                            content = result.get("result", "工具执行成功，但未返回结果")
                            yield {"type": "system", "content": f"\033[93m[工具 '{tc['function']['name']}' 执行结果]: {content[:50]}...\033[0m\n"}
                            stdout = result.get("stdout", "")
                            if stdout:
                                content += f"\n[工具执行过程输出]: {stdout}"
                                yield {"type": "system", "content": f"\033[94m[工具 '{tc['function']['name']}' 执行过程输出]: {stdout[:50]}...\033[0m\n"}
                        else:
                            content = f"Error: 工具执行失败，错误信息: {result.get('error', '未知错误')}"
                            yield {"type": "system", "content": f"\033[91m[工具 '{tc['function']['name']}' 执行失败]: {content}\033[0m\n"}
                            stderr = result.get("stderr", "")
                            stdout = result.get("stdout", "")
                            if stderr:
                                content += f"\n[工具执行过程错误输出]: {stderr}"
                                yield {"type": "system", "content": f"\033[91m[工具 '{tc['function']['name']}' 执行过程错误输出]: {stderr[:50]}...\033[0m\n"}
                            if stdout:
                                content += f"\n[工具执行过程输出]: {stdout}"
                                yield {"type": "system", "content": f"\033[94m[工具 '{tc['function']['name']}' 执行过程输出]: {stdout[:50]}...\033[0m\n"}
                            tool_result = content
                        req_messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": tool_result
                        })


                    elif tc["function"]["name"] == "max_tool_calls_exceeded":
                        tool_result = "Error: 已达到最大工具调用次数限制，系统强制拦截所有工具调用。请停止尝试调用任何工具"
                        req_messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": tool_result
                        })
                    else:
                        tool_result = f"Error: Tool '{tc['function']['name']}' 不存在。请勿再次调用该工具"
                        req_messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": tool_result
                        })

                # 走到这里，循环会自动继续进入下一轮 (带着包含 tool 结果的 req_messages 去重新请求大模型)
            else:
                # 如果没有触发工具，说明模型已经给出了最终答案，跳出循环
                break
        if get_user_inputs or get_user_questions:
            yield {"type": "meta", "assistant_questions": get_user_questions, "user_inputs": get_user_inputs}
        if tool_call_history:
            yield {"type": "meta", "tool_call_history": tool_call_history}

        client.close()