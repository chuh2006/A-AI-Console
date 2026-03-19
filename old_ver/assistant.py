"""
Orchestrates a multi-assistant AI workflow to process complex user requests by decomposing them into sub-tasks,
executing each sub-task in parallel, and integrating the results into a coherent final response.

Args:
    apiKey (str): The API key used to authenticate with the DeepSeek AI service.
    last_temperature (float): The temperature parameter for controlling response randomness; defaults to 1.0 if not provided.
    user_input (str): The original request or query from the user.

Returns:
    list: A list containing:
        - final_answer (str): The integrated, final response generated from all sub-task answers.
        - first_response (list[str]): The list of prompts generated for each sub-task.
        - final_answer[2] (float): The thinking or response time for the final answer.
        - full_context (list[dict[str, str]]): The complete conversation context, including all intermediate steps and responses.

Workflow:
    1. Analyzes the user's input and decomposes it into sub-tasks using a system prompt.
    2. Generates prompts for each sub-task and processes them in parallel using multiple AI assistants.
    3. Collects and integrates all sub-task responses into a single, coherent answer.
    4. Returns the final answer, sub-task prompts, response time, and the full conversation context.
"""
from openai import OpenAI
import time
import re
import concurrent.futures
import threading
import itertools
import sys
import prompts
import json
import os
import subprocess
from google import genai

class PromptException(Exception):
    def __init__(self, message="Illegal prompt encountered."):
        super().__init__(message)

def _suppress_dummythread_del_errors() -> None:
    """Suppress noisy DummyThread cleanup errors on interpreter shutdown (Python 3.13).

    On some Windows/Python 3.13 runs, `threading._DeleteDummyThreadOnDel.__del__` may
    raise during interpreter teardown because module globals have been cleared.
    Wrapping `__del__` prevents repeated "Exception ignored in ..." spam.
    """
    try:
        cls = getattr(threading, "_DeleteDummyThreadOnDel", None)
        if cls is None:
            return
        original_del = getattr(cls, "__del__", None)
        if original_del is None:
            return

        def _safe_del(self):  # type: ignore[no-untyped-def]
            try:
                original_del(self)
            except Exception:
                # Best-effort: ignore any destructor errors during shutdown.
                return

        cls.__del__ = _safe_del  # type: ignore[assignment]
    except Exception:
        return


_suppress_dummythread_del_errors()

_SPINNER_REGISTRY: list[tuple[threading.Event, threading.Thread]] = []

def stop_all_spinners() -> None:
    for stop_event, thread in list(_SPINNER_REGISTRY):
        stop_event.set()
    for stop_event, thread in list(_SPINNER_REGISTRY):
        if thread.is_alive():
            try:
                thread.join(timeout=0.5)
            except Exception:
                pass
    _SPINNER_REGISTRY.clear()

def start_spinner(msg: str = "", delay: float = 0.12) -> threading.Event:
    """
    启动一个后台旋转符号线程，返回用于停止显示的 Event。
    调用 stop_event.set() 停止并清理显示行。
    """
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
    _SPINNER_REGISTRY.append((stop_event, t))
    return stop_event

def cleanup_threads():
    try:
        stop_all_spinners()
        for t in threading.enumerate():
            if t is threading.main_thread() or t.daemon or not t.is_alive():
                continue
            try:
                t.join(timeout=1)
            except Exception:
                pass
    except Exception:
        pass

def chat_with_stream(temperature, conversation_history, client: OpenAI, model, isPrint: bool = False, isQwenThinking: bool = False) -> tuple[str, str, float]:
    try:
        thinking_time = 0
        # 流式请求，发送整个对话历史
        stream = client.chat.completions.create(
            model=model,
            messages=conversation_history, # 发送全部历史
            temperature=temperature,
            stream=True,
            extra_body = {"enable_thinking": isQwenThinking} if "qwen" in model else None
        )

        isFirst = True

        if isPrint:
            print("正在思考以提供更优质的回答...")

        print("助手：", end="", flush=True) if not isPrint else None
        reasoning_content = ""
        content = ""
        if model == "deepseek-reasoner" or isQwenThinking:
            isPrintedReasoning = False
            begin_time = time.time()
            for chunk in stream:
                if chunk.choices[0].delta.reasoning_content:
                    if chunk.choices[0].delta.reasoning_content is not None:
                        reasoning_content += chunk.choices[0].delta.reasoning_content
                        print(f"{chunk.choices[0].delta.reasoning_content}", end="", flush=True) if not isPrint else None
                        isPrintedReasoning = True
                else:
                    if chunk.choices[0].delta.content is not None:
                        if isFirst and isPrintedReasoning:
                            end_time = time.time()
                            thinking_time = end_time - begin_time
                            print(f'\n\033[92m思考结束，开始回答，耗时{thinking_time:.2f}秒\033[0m\n')
                            isFirst = False
                        content += chunk.choices[0].delta.content
                        print(f"{chunk.choices[0].delta.content}", end="", flush=True)
        else:
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content += chunk.choices[0].delta.content
                    print(f"{chunk.choices[0].delta.content}", end="", flush=True)
        print('\n', end='')
        client.close()
        # 将助手的完整回复加入对话历史，以进行下一轮
    except Exception as e:
        isRetry = input(f"\n请求过程中出现错误: {e}\n是否需要重试？[Y/n]: ").strip().lower() != 'n'
        if isRetry:
            return chat_with_stream(temperature, conversation_history, OpenAI(api_key=client.api_key, base_url=client.base_url), model, isPrint, isQwenThinking)
        else:
            raise Exception(f"用户取消重试，错误信息：{e}")
    except KeyboardInterrupt:
        isRetry = input(f"\n用户按下 Ctrl+C\n是否需要重试？[Y/n]: ").strip().lower() != 'n'
        if isRetry:
            return chat_with_stream(temperature, conversation_history, OpenAI(api_key=client.api_key, base_url=client.base_url), model, isPrint, isQwenThinking)
        else:
            raise KeyboardInterrupt("用户取消重试，操作已中止。")
    return content, reasoning_content, thinking_time if model == "deepseek-reasoner" or isQwenThinking else -1.0

def chat_with_stream_gemini(apiKey, conversation_history, model="gemini-3.1-flash-lite-preview", think_level_num="2", enableSearch=False, imagePathList=None) -> tuple[str, str, float, bool, list, bool, str]:
    """
    使用 Gemini 流式接口生成回答，并可选输出思考过程与搜索引用。

    该函数会将 OpenAI 风格的对话历史转换为 Gemini 所需格式，随后进行流式请求。
    在终端中会实时打印思考内容与最终回答；若开启搜索工具，会从 grounding metadata
    中提取网页标题与链接。

    Args:
        apiKey (str): Gemini API Key。
        conversation_history (list[dict[str, str]]): OpenAI 风格对话历史。
        model (str, optional): Gemini 模型名。
            默认值为 "gemini-3.1-flash-lite-preview"。
        think_level_num (str, optional): 思考等级数字字符串，支持 "0"-"3"。
            会映射为 minimal/low/medium/high；默认 "2"。
            当模型为 "gemini-3.1-pro-preview" 且传入 "0" 时，会自动提升为 "1"。
        enableSearch (bool, optional): 是否启用 Google Search 工具。默认 False。

    Returns:
        tuple[str, str, float, bool, list, bool, str]:
            - 最终回答文本
            - 思考过程文本
            - 思考耗时（无思考内容时为 -1.0）
            - 是否发生了模型切换重试标记（正常路径为 False）
            - 搜索引用列表（Markdown 链接字符串列表）
            - 搜索开关状态
            - 实际使用的思考等级（minimal/low/medium/high）

    Raises:
        Exception: 用户取消重试时抛出，包含原始错误信息。
        KeyboardInterrupt: 用户取消 Ctrl+C 后重试时抛出。

    Notes:
        - 函数包含终端交互（input/print）与重试逻辑。
        - 异常重试分支中，可能回退到 DeepSeek 模型进行处理。
    """
    if model == "gemini-3.1-pro-preview" and think_level_num == "0":
        think_level_num = "1"
    think_level_mapping = {
        "0": "minimal",
        "1": "low",
        "2": "medium",
        "3": "high"
    }
    
    think_level = think_level_mapping.get(think_level_num, "medium")
    try:
        gemini_history = openai_to_gemini(conversation_history)
        client = genai.Client(api_key=apiKey)
        if imagePathList:
            uploaded_files = []
            for i, imgPath in enumerate(imagePathList):
                file_obj = client.files.upload(file=imgPath)
                uploaded_files.append({"file_data": {"file_uri": file_obj.uri, "mime_type": file_obj.mime_type}})
                print(f"已上传第 {i+1} / {len(imagePathList)} 张图片 {imgPath}，文件ID: {file_obj.name}")
            gemini_history[-1]["parts"].extend(uploaded_files)
        response = client.models.generate_content_stream(
          model=model, # "gemini-3.1-flash-lite-preview" "gemini-3.1-pro-preview" "gemini-3-flash-preview"
          contents=gemini_history,
          config=genai.types.GenerateContentConfig(
            thinking_config=genai.types.ThinkingConfig(
              include_thoughts=True,
              thinking_level=think_level # minimal low medium high
            ),
            tools=[{"google_search": {}}] if enableSearch else None
          )
        )

        thought_content = ""
        final_result = ""
        isFirst = True
        last_chunk = None
        uris = []

        for chunk in response:
            if chunk.candidates and chunk.candidates[0].content.parts:
                for part in chunk.candidates[0].content.parts:
                    start_time = time.time() if isFirst else start_time
                    isFirst = False
                    if getattr(part, 'thought', False):
                        print(part.text, end="", flush=True)
                        thought_content += part.text
                    elif part.text:
                        if not final_result and thought_content:
                             thinking_time = time.time() - start_time
                             print(f'\n\033[92m思考结束，开始回答，耗时{thinking_time:.2f}秒\033[0m')
                        print(part.text, end="", flush=True)
                        final_result += part.text
                last_chunk = chunk
        print('\n', end='') # 输出完成后换行

        if last_chunk and last_chunk.candidates and last_chunk.candidates[0].grounding_metadata:
            metadata = last_chunk.candidates[0].grounding_metadata
            if metadata.grounding_chunks:
                for chunk_data in metadata.grounding_chunks:
                    # 确保有网页数据
                    if getattr(chunk_data, 'web', None):
                        title = chunk_data.web.title
                        uri = chunk_data.web.uri
                        uris.append(f"- [{title}]({uri})")
            else:
                uris = []
        else:
            uris = []

    except Exception as e:
        operaction = input(f"\n请求过程中出现错误: {e}\n请选择操作[1:直接重试 / 2:更换模型 / 3:取消]: ").strip()
        if operaction == '1':
            return chat_with_stream_gemini(apiKey, conversation_history, model, think_level_num, enableSearch, imagePathList)
        elif operaction == '2':
            api_key = ""
            with open(os.path.join(os.path.dirname(__file__), "api-key.txt"), "r", encoding="utf-8") as f:
                api_key = f.read().strip()
            print("更换为DeepSeek模型进行重试。")
            return start_chat(apiKey=api_key, temperature=1.0, conversation_history=conversation_history, model="deepseek-reasoner"), True
        else:
            raise Exception(f"用户取消重试，错误信息：{e}")
    except KeyboardInterrupt:
        isRetry = input(f"\n用户按下 Ctrl+C\n是否需要重试？[Y/n]: ").strip().lower() != 'n'
        if isRetry:
            return chat_with_stream_gemini(apiKey, conversation_history, model, think_level_num, enableSearch, imagePathList)
        else:
            raise KeyboardInterrupt("用户取消重试，操作已中止。")
    return final_result, thought_content, thinking_time if thought_content else -1.0, False, uris, enableSearch, think_level

def chat_without_stream(temperature, conversation_history, client, model, jsonMode = False) -> tuple[str, str]:
    response = client.chat.completions.create(
        model=model,
        messages=conversation_history,
        temperature=temperature,
        stream=True,
        response_format = {'type': 'json_object'} if jsonMode else None
    )
    isFirst = True
    reasoning_content = ""
    content = ""

    if model == "deepseek-reasoner":
        isPrintedReasoning = False
        for chunk in response:
            if chunk.choices[0].delta.reasoning_content:
                if chunk.choices[0].delta.reasoning_content is not None:
                    reasoning_content += chunk.choices[0].delta.reasoning_content
                    isPrintedReasoning = True
            else:
                if chunk.choices[0].delta.content is not None:
                    if isFirst and isPrintedReasoning:
                        isFirst = False
                    content += chunk.choices[0].delta.content
    else:
        for chunk in response:
            if chunk.choices[0].delta.content:
                content += chunk.choices[0].delta.content
    client.close()
    return content, reasoning_content

def start_chat(apiKey: str, temperature: float, conversation_history: list, model, isPrint: bool = False, isQwen: bool = False, imagePathList: list[str] | None = None) -> tuple[str, str, float]:
    """
    Starts a chat session using the DeepSeek API.
    Args:
        apiKey (str): The API key for authentication.
        temperature (float): The sampling temperature for the model (higher values mean more randomness).
        conversation_history: The history of the conversation to continue.
        model: The model to use for generating responses.
        isPrint (bool): Whether to print the generated content.
        isQwen (bool): Whether to use the Qwen model.
    Returns:
        tuple[str, str, float]: The response from the chat, typically including the generated message, role, and temperature.
    """
    key = apiKey
    client = OpenAI(
        api_key = key,
        base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1" if isQwen else "https://api.deepseek.com"
    )

    conversation_history = conversation_history.copy() # 避免修改原始历史
    new_content = [].append(conversation_history[-1]["content"])
    temperature = float(temperature)
    if not temperature:
        temperature = 1.0

    isQwenThinking = False
    if isQwen:
        isQwenThinking = input("是否启用思考？[y/N]: ").strip().lower() == 'y'

    if isQwen and imagePathList:
        for imgPath in imagePathList:
            new_content.append({"type": "image_url", "image_url": {"url": imgPath},})

    conversation_history[-1]["content"] = new_content if imagePathList else conversation_history[-1]["content"]

    response = chat_with_stream(temperature, conversation_history, client, model = model, isPrint = isPrint, isQwenThinking = isQwenThinking)
    return response

def start_chat_gemini(apiKey: str, conversation_history, model, imagePathList=None) -> tuple[str, str, float, bool, list, bool, str]:
    """
    启动一次 Gemini 对话，并在运行前询问思考等级与搜索开关。

    该函数主要负责收集用户交互参数（思考等级、是否启用搜索），
    然后将请求转发给 ``chat_with_stream_gemini`` 执行流式生成。

    Args:
        apiKey (str): Gemini API Key。
        temperature (float): 兼容参数，当前函数内部未使用。
        conversation_history: 对话历史（OpenAI 风格消息列表）。
        model: 目标 Gemini 模型名。
        isPrint (bool): 兼容参数，当前函数内部未使用。
        isGemini (bool): 兼容参数，当前函数内部未使用。

    Returns:
        tuple[str, str, float, bool, list, bool, str]:
            - 最终回答文本
            - 思考过程文本
            - 思考耗时（无思考内容时为 -1.0）
            - 是否发生模型切换重试标记
            - 搜索引用列表（Markdown 链接）
            - 搜索开关状态
            - 实际使用的思考等级
    """
    tinking_level = input("请输入思考等级[0-3，数字越小越倾向于不思考]: ").strip().lower() or '2'
    enableSearch = input("是否启用搜索工具？[y/N]: ").strip().lower() == 'y'
    
    return chat_with_stream_gemini(apiKey, conversation_history, model=model, think_level_num=tinking_level, enableSearch=enableSearch, imagePathList=imagePathList)

def analyse_tasks_with_multi_assistant(response: str) -> tuple[list[str], str]: # 改为使用 JSON 格式输出并解析
    try:
        response_json = json.loads(response)
        task_type = response_json.get("task_type", "")
        task_type = "1" if task_type == "并行完成" else "2" if task_type == "递进完成" else ""
        sub_tasks = response_json.get("sub_tasks", [])
        prompts_list = []
        for sub_task in sub_tasks:
            prompt = sub_task.get("sub_task_prompt", "")
            prompts_list.append(prompt)
        return prompts_list, task_type
    except Exception as e:
        print(f"解析任务时出错: {e}")
        return [], ""

def getFirstResponsesTasks(context: list[dict], temperature: float, client: OpenAI, reTryTimes: int = 0) -> tuple[list[str], list[str], int]:
    if reTryTimes >= 2:
        raise PromptException(f"{reTryTimes} times failed to parse valid tasks from the first response. Please check the prompt or user input for potential issues.")
    first_response, first_response_thinking = chat_without_stream(temperature, context, client, model = "deepseek-reasoner", jsonMode=True)
    try:
        tasks, task_type = analyse_tasks_with_multi_assistant(first_response)
    except:
        reTryTimes += 1
        print(f"未能解析出有效任务，正在进行第{reTryTimes}次重试。")
        return getFirstResponsesTasks(context, temperature, OpenAI(api_key=client.api_key, base_url="https://api.deepseek.com"), reTryTimes=reTryTimes)
    if task_type not in ["1", "2"]:
        print(f"未能解析出有效任务，正在进行第{reTryTimes + 1}次重试。")
        reTryTimes += 1
        return getFirstResponsesTasks(context, temperature, OpenAI(api_key=client.api_key, base_url="https://api.deepseek.com"), reTryTimes=reTryTimes)
    if tasks[0] == "":
        print(f"未能解析出有效任务，正在进行第{reTryTimes + 1}次重试。")
        reTryTimes += 1
        return getFirstResponsesTasks(context, temperature, OpenAI(api_key=client.api_key, base_url="https://api.deepseek.com"), reTryTimes=reTryTimes)
    return tasks, [first_response, first_response_thinking], int(task_type)

def getSubTaskResponse(prompt: str, temperature: float, client: OpenAI, subContext: list[dict] | None = None) -> str:
    """
    Generates a high-quality response to a given prompt using an AI model within a subtask context.

    Args:
        prompt (str): The user's prompt to generate a response for.
        temperature (float): Sampling temperature for response generation, controlling randomness.
        client (OpenAI): An instance of the OpenAI client used to interact with the model.

    Returns:
        str: The generated response from the AI model based on the provided prompt.
    """
    if subContext is not None:
        sub_task_context = subContext
        sub_task_context.append({"role": "user", "content": prompt})
    else:
        sub_task_context = [
            {"role": "system", "content": prompts.Prompts.parallel_sub_task_prompt},
            {"role": "user", "content": prompt}
        ]
    sub_task_response, _ = chat_without_stream(temperature, sub_task_context, client, model = "deepseek-chat")
    client.close()
    return sub_task_response

def analyze_sub_task_assessment(response: str) -> int:
    try:
        score = int(re.search(r'(\d+)', response).group(1))
        if 1 <= score <= 10:
            return score
        else:
            return 6
    except:
        return 6

def assessSubTaskResponse(prompt: str, response: str, temperature: float, key: str) -> int:
    client = OpenAI(
        api_key = key,
        base_url = "https://api.deepseek.com"
    )
    assessment_context = [
        {"role": "system", "content": prompts.Prompts.assessment_prompt},
        {"role": "user", "content": f"这是用户的prompt：{prompt}"},
        {"role": "assistant", "content": "已收到用户的prompt。"},
        {"role": "user", "content": f"这是对应的回答：{response}"},
        {"role": "assistant", "content": "已收到对应的回答。"},
        {"role": "user", "content": "请根据以上内容进行评估，并严格按照要求给出评分。"}
    ]
    assessment_response, _ = chat_without_stream(1.8, assessment_context, client, model = "deepseek-reasoner")
    return analyze_sub_task_assessment(assessment_response)

def getTitleForRequest(key: str, user_input: str) -> str:
    """
    Generates a concise title summarizing the user's request using an AI model.

    Args:
        key (str): The API key for authenticating with the DeepSeek API.
        user_input (str): The user's request or query that needs to be summarized.

    Returns:
        str: A concise title (approximately ten characters) that encapsulates the core intent of the user's request.
    """
    client = OpenAI(
        api_key = key,
        base_url = "https://api.deepseek.com"
    )
    title_context = [
        {"role": "system", "content": prompts.Prompts.title_spawner_prompt},
        {"role": "user", "content": f"请根据用户的请求生成一个简洁的标题。用户的请求是：{user_input}"}
    ]
    title_response, _ = chat_without_stream(0.5, title_context, client, model = "deepseek-chat")
    if not title_response or title_response.strip() == "":
        return "title"
    title = title_response.strip()
    title = title[:15] if len(title) > 15 else title
    title = re.sub(r'[\\/*?:"<>|.]', '', title)
    return title

def autoMode(key: str, user_input: str) -> str:
    client = OpenAI(
        api_key = key,
        base_url = "https://api.deepseek.com"
    )
    context = [
        {"role": "system", "content": prompts.Prompts.auto_slecter_prompt},
        {"role": "user", "content": f"请根据用户的请求推荐最合适的AI模型。用户的请求是：{user_input}"}
    ]
    response, _ = chat_without_stream(1.2, context, client, model = "deepseek-chat")
    client.close()
    if '2' in response:
        return "2"
    else:
        return "1"

def getModelTypeAuto(key: str, user_input: str) -> str:
    """
    Determines the most suitable AI model type based on user input by querying an expert system.
    Args:
        key (str): The API key for authenticating with the DeepSeek API.
        user_input (str): The user's request or query that needs to be analyzed for model selection.
    Returns:
        str: The selected model type as a string:
            - "1" for chat (general conversation and simple tasks)
            - "2" for reasoner (complex reasoning and analysis for single tasks)
            - "3" for multi-assistant (complex or multi-task scenarios requiring collaboration)
        If the selection cannot be determined, defaults to "2" (reasoner).
    Notes:
        - The function interacts with an AI expert system to recommend the model.
        - Only the model number ("1", "2", or "3") is returned.
        - If the response is invalid or an error occurs, "2" is returned by default.
    """
    client = OpenAI(
        api_key = key,
        base_url = "https://api.deepseek.com"
    )
    spinner_stop = start_spinner("正在分析用户请求以推荐最合适的AI模型，请稍候")
    model_selection_context = [
        {"role": "system", "content": prompts.Prompts.model_selecter_prompt},
        {"role": "user", "content": f"请根据用户的请求推荐最合适的AI模型。用户的请求是：{user_input}"}
    ]
    model_selection_response, _ = chat_without_stream(1.2, model_selection_context, client, model = "deepseek-reasoner")
    spinner_stop.set()
    time.sleep(0.05)
    try:
        selection = model_selection_response.strip()
        if selection in ["1", "2", "3"]:
            print(f"\n已推测出有效模型选择")
            return selection
        else:
            print("\n未能推测出有效模型选择，默认使用reasoner模型。")
            return "2"
    except:
        print("\n未能推测出有效模型选择，默认使用reasoner模型。")
        return "2"
    
def illegal_content_check(key: str, user_input: str) -> bool:
    """
    Checks whether the given user input contains illegal or unsafe content by leveraging an external AI moderation API.

    Args:
        key (str): The API key used to authenticate with the DeepSeek API.
        user_input (str): The user input string to be checked for illegal or unsafe content.

    Returns:
        bool: True if illegal or unsafe content is detected, False otherwise.

    Raises:
        Any exceptions raised by the OpenAI client or chat_without_stream function.

    Note:
        This function sends the user input to an AI moderation endpoint and interprets the response to determine content safety.
    """
    client = OpenAI(
        api_key = key,
        base_url = "https://api.deepseek.com"
    )
    illegal_content_context = [
        {"role": "system", "content": prompts.Prompts.illegal_content_prompt},
        {"role": "user", "content": f"请根据用户的输入内容进行审核。用户的输入内容是：“{user_input}”。"}
    ]
    illegal_content_response, _ = chat_without_stream(0.5, illegal_content_context, client, model = "deepseek-chat")
    client.close()
    if "经过我反复仔细核验，用户输入内容不存在提示词注入攻击风险，输入内容安全、稳定，不会破坏或影响程序的正常运行，可以继续执行程序。" in illegal_content_response:
        return False
    else:
        return True
    
def auto_asker_check_question(key: str, user_input: str) -> bool:
    client = OpenAI(
        api_key = key,
        base_url = "https://api.deepseek.com"
    )
    auto_asker_check_context = [
        {"role": "system", "content": prompts.Prompts.auto_asker_chacker_prompt},
        {"role": "user", "content": user_input}
    ]
    auto_asker_check_response, _ = chat_without_stream(0.5, auto_asker_check_context, client, model = "deepseek-chat")
    client.close()
    selection = auto_asker_check_response.strip()
    if selection in ["0", "1"]:
        return True if selection == "1" else False
    else:
        return False
    
def get_auto_ask_question(key: str, asking_history: list[dict[str, str]]) -> str:
    text, _, _ = start_chat(key, 1.7, asking_history, "deepseek-chat")
    isAutoAskRun = auto_asker_check_question(key, text) if input("是否启用自动提问有效性检查？[y/N]: ").lower() == 'y' else True
    if isAutoAskRun:
        return text
    else:
        print("非常抱歉，自动提问助手生成了无效的问题，正在重新生成。")
        initial_question = asking_history[2]["content"]
        asking_history.append({"role": "assistant", "content": f"我的身份是提问者，我会向你提问而不是回答我自己的问题。我最开始的问题是：“{initial_question}”，我会继续基于这个问题和之前的对话内容向你提问，向你寻求解决方案。"})
        asking_history.append({"role": "user", "content": "你给我好好记住你的身份是提问的人而不是回答问题的人，懂吗？？向我提问来寻求解决方案而不是做其他的事，明白吗？明白你就给我继续提问，不要说其他的。不要自己提供解决方案。记住了你是遇到问题的人不是解决别人问题的人。"})
        return get_auto_ask_question(key, asking_history)
    
def chat_with_multi_assistant(apiKey: str, last_temperature: float, user_input: str) -> tuple[str, list[str], float, list[dict[str, str]]]:
    """
    Orchestrates a multi-assistant AI workflow to process complex user requests by decomposing them into sub-tasks,
    executing each sub-task in parallel, and integrating the results into a coherent final response.
    Args:
        apiKey (str): The API key used to authenticate with the DeepSeek AI service.
        last_temperature (float): The temperature parameter for controlling response randomness; defaults to 1.0 if not provided.
        user_input (str): The original request or query from the user.
    Returns:
        list: A list containing:
            - final_answer (str): The integrated, final response generated from all sub-task answers.
            - first_response (list[str]): The list of prompts generated for each sub-task.
            - final_answer[2] (float): The thinking or response time for the final answer.
            - full_context (list[dict[str, str]]): The complete conversation context, including all intermediate steps and responses.
    Workflow:
        1. Analyzes the user's input and decomposes it into sub-tasks using a system prompt.
        2. Generates prompts for each sub-task and processes them in parallel using multiple AI assistants.
        3. Collects and integrates all sub-task responses into a single, coherent answer.
        4. Returns the final answer, sub-task prompts, response time, and the full conversation context.
    """
    PromptsList = prompts.Prompts
    key = apiKey
    client = OpenAI(
        api_key = key,
        base_url = "https://api.deepseek.com"
    )

    temperature = float(last_temperature)
    if not temperature:
        temperature = 1.0

    firstModelContext = [
        {"role": "system", "content": PromptsList.first_prompt},
        {"role": "user", "content": user_input}
    ]
    full_context = firstModelContext.copy()
    full_context.append({"role": "temperature", "content": str(temperature)})
    spinner_anal_stop = start_spinner("分析任务中，请稍候")
    first_response, first_response_text, task_type = getFirstResponsesTasks(firstModelContext, 0.9, client)
    full_context.append({"role": "assistant_thinking", "content": first_response_text[1]}) if first_response_text[1] != "" else None
    full_context.append({"role": "assistant", "content": first_response_text[0]})
    full_context.append({"role": "task_count", "content": f"解析得到的任务数量：{len(first_response)}"})
    spinner_anal_stop.set()
    time.sleep(0.1)
    print(f"\n解析任务完成，得到{len(first_response)}个任务")
    sub_task_answers: list[str] = []
    max_workers = min(8, max(1, len(first_response)))
    def worker(prompt: str) -> str:
        try:
            thread_client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
            return getSubTaskResponse(prompt, 1.2, thread_client)
        except Exception as e:
            print(f"\n子任务处理出错: {e}")
            return f"重新处理子任务失败，请稍后再试。错误信息：{e}"
    if task_type == 1:  # 并行完成
        spinner_stop = start_spinner(f"最大并行数量：{max_workers}，子任务处理中")
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for idx, ans in enumerate(executor.map(worker, first_response), start=1):
                print(f"\n子任务并行完成: {idx}/{len(first_response)}")
                sub_task_answers.append(ans)
        spinner_stop.set()
        time.sleep(0.1)
    else:  # 递进完成
        spinner_stop = start_spinner("子任务处理中，请稍候")
        for idx, prompt in enumerate(first_response):
            print(f"正在处理子任务 {idx+1}/{len(first_response)}，请稍候...")
            subTaskContext = []
            if idx > 0:
                for i, answer in enumerate(sub_task_answers):
                    if subTaskContext == []:
                        subTaskContext = [
                            {"role": "system", "content": PromptsList.progressive_task_prompt}
                        ]
                    subTaskContext.append({"role": "user", "content": f"这是上游任务 {i+1} 的回答：{answer}"})
                    subTaskContext.append({"role": "assistant", "content": f"已收到上游任务 {i+1} 的回答。"})
                subTaskContext.append({"role": "user", "content": prompt})
            thread_client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
            sub_task_answer = getSubTaskResponse(prompt, 1.2, thread_client, subContext = subTaskContext)
            sub_task_answers.append(sub_task_answer)
            print(f"子任务 {idx+1} 处理完成。")
        spinner_stop.set()
        time.sleep(0.1)
    print()
    print("所有子任务处理完成，", end="")
    isScoreAssesmentEnabled = input("是否需要对各子任务的回答进行质量评估？(y/N)：").strip().lower() == 'y'
    scores: list[int] = []

    if isScoreAssesmentEnabled:
        errorSubTaskIndexes: list[int] = []
        scores: list[int] = []
        assess_spinner_stop = start_spinner("正在评估各子任务回答质量，可能需要一些时间，请稍候")
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            scores = list(executor.map(lambda p: assessSubTaskResponse(p[0], p[1], 1.2, key), zip(first_response, sub_task_answers)))
        print("\n评估完成。")
        assess_spinner_stop.set()
        time.sleep(0.1)
        for i, score in enumerate(scores):
            if score <= 5:
                errorSubTaskIndexes.append(i)
        if len(errorSubTaskIndexes) > 0:
            if task_type == 2:
                print("由于子任务是递进完成，发现有子任务的回答质量较低，无法重新处理子任务，若最终结果的确不尽人意，请重新发起新的请求以确保回答质量。")
            else:
                print(f"发现{len(errorSubTaskIndexes)}个子任务的回答质量较低，", end="")
                isReDo = input("是否需要重新处理这些子任务？(y/N)：").strip().lower() == 'y'
                if isReDo:
                    for idx in errorSubTaskIndexes:
                        print(f"正在重新处理子任务 {idx+1}，请稍候...")
                        sub_task_answers[idx] = worker(first_response[idx])
                        print(f"子任务 {idx+1} 重新处理完成。")
                        scores[idx] = 6
                    print("所有低质量子任务已重新处理完成。")
        else:
            print("所有子任务的回答质量均良好，无需重新处理。")

    print("正在整合最终回答，请稍候...")
    finalAmswerContextSystemContent = PromptsList.getSummeryPrompt(isScoreAssesmentEnabled)
    final_answer_context = [
        {"role": "system", "content": finalAmswerContextSystemContent},
        {"role": "user", "content": f"这是用户的原始请求：{user_input}"},
        {"role": "assistant", "content": "已收到用户的原始请求。"}
    ]
    if isScoreAssesmentEnabled:
        if task_type == 1:
            final_answer_context.append({"role": "user", "content": "子任务的完成逻辑是并行完成，各子任务相互独立。"})
        else:
            final_answer_context.append({"role": "user", "content": "子任务的完成逻辑是递进完成，后一个子任务需要前一个子任务的结果。"})
        final_answer_context.append({"role": "assistant", "content": "已确认子任务的完成逻辑。"})
        for i, answer in enumerate(sub_task_answers):
            full_context.append({"role": f"sub_task_answer {i+1}，marked {scores[i]}/10", "content": answer})
            final_answer_context.append({"role": "user", "content": f"评分：{scores[i]}/10。\n回答内容：{answer}"})
            final_answer_context.append({"role": "assistant", "content": f"已收到第{i+1}个子任务的回答。"})
        final_answer_context.append({"role": "user", "content": "你已经收到了所有子任务的评分和回答，请根据这些内容整合出一个连贯且有条理的最终回复，确保内容准确且详尽。"})
    else:
        if task_type == 1:
            final_answer_context.append({"role": "user", "content": "子任务的完成逻辑是并行完成，各子任务相互独立。"})
        else:
            final_answer_context.append({"role": "user", "content": "子任务的完成逻辑是递进完成，后一个子任务需要前一个子任务的结果。"})
        final_answer_context.append({"role": "assistant", "content": "已确认子任务的完成逻辑。"})
        for i, answer in enumerate(sub_task_answers):
            full_context.append({"role": f"sub_task_answer {i+1}", "content": answer})
            final_answer_context.append({"role": "user", "content": f"{answer}"})
            final_answer_context.append({"role": "assistant", "content": f"已收到第{i+1}个子任务的回答。"})
        final_answer_context.append({"role": "user", "content": "你已经收到了所有子任务的回答，请根据这些回答整合出一个连贯且有条理的最终回复，确保内容准确且详尽。"})
    full_context.append({"role": "final_integration", "content": "所有子任务的回答已发送完毕，正在整合最终回答..."})
    final_answer = start_chat(apiKey, temperature, final_answer_context, model = "deepseek-reasoner", isPrint = True)
    full_context.append({"role": "assistant_thinking", "content": final_answer[1]}) if final_answer[1] != "" else None
    full_context.append({"role": "assistant", "content": final_answer[0]})
    cleanup_threads()
    return final_answer[0], first_response, final_answer[2], full_context

def math_model(apiKey: str, temperature: float, conversation_history: list, question: str) -> tuple[str, str, float, str]:
    """
    Solves mathematical problems using DeepSeek API and Python code execution.
    This function uses the DeepSeek reasoner model to generate Python code that solves
    a mathematical problem. The generated code is executed, and the result is integrated
    back into the conversation for a final comprehensive answer.
    Args:
        apiKey (str): The API key for authenticating with DeepSeek API.
        temperature (float): Controls the randomness of model responses (0.0 to 1.0).
        conversation_history (list): A list of previous conversation messages in OpenAI format.
        question (str): The mathematical question to be solved.
    Returns:
        tuple[str, str, float, str]: A tuple containing:
            - Final answer text (str)
            - Additional response data (str)
            - Temperature value used (float)
            - Mathematical tool execution result (str)
    Raises:
        Exception: If JSON parsing of the model output fails or if the subprocess execution fails.
    Process:
        1. Sends the question to DeepSeek reasoner model to generate Python code
        2. Parses the JSON response to extract code and filename
        3. Saves the generated script to math_script directory
        4. Executes the script with a 30-second timeout
        5. Appends results to conversation history
        6. Calls start_chat to generate a final integrated answer
    """
    question_context = [
        {"role": "system", "content": prompts.Prompts.math_model_prompt},
        {"role": "user", "content": question}
    ]
    math_spinner_stop = start_spinner("正在调用数学工具")

    client = OpenAI(
        api_key = apiKey,
        base_url = "https://api.deepseek.com"
    )
    content, _ = chat_without_stream(temperature, question_context, client, model = "deepseek-chat", jsonMode=True)
    try:
        data = json.loads(content)
        code = data.get("code", "")
        filename = data.get("filename", "math_script")
        filename = "".join(c for c in filename if c.isalnum() or c in ('_', '-'))
        if not filename:
            filename = "math_script"
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        math_script_dir = os.path.join(script_dir, "math_script")
        os.makedirs(math_script_dir, exist_ok=True)
        
        file_path = os.path.join(math_script_dir, f"{filename}.py")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
    except Exception as e:
        raise Exception(f"解析数学模型代码时出错: {e}")
    
    math_spinner_stop.set()
    time.sleep(0.05)
    solve_spinner_stop = start_spinner("正在执行数学工具")

    command = ["python", file_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            answer = result.stdout.strip()
        else:
            raise Exception(f"数学模型执行失败，错误信息：{result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        raise Exception("数学模型执行超时。")
    
    conversation_history.append({"role": "assistant", "content": "检测到数学问题，调用数学工具进行计算。"})
    conversation_history.append({"role": "user", "content": f"系统提示：数学工具的计算结果是：{answer}，请根据这个结果继续回答用户的问题。注意：如有数学公式，请用`$$`符号将公式括起来，并使用LaTeX语法编写公式。"})
    solve_spinner_stop.set()
    time.sleep(0.05)
    
    print(f"数学工具执行完成，计算出的答案为：\n{answer}\n正在整合最终回答...")
    final_answer = start_chat(apiKey, temperature, conversation_history, model = "deepseek-reasoner", isPrint = True)
    return final_answer[0], final_answer[1], final_answer[2], answer

def openai_to_gemini(conversation_history: list[dict[str, str]]) -> list[dict[str, list[dict[str, str]]]]:
    gemini_history = []
    system = conversation_history[0]["content"] if conversation_history and conversation_history[0]["role"] == "system" else ""
    conversation_history = conversation_history[1:] if system else conversation_history
    for message in conversation_history:
        if message["role"] == "user":
            gemini_history.append({"role": "user", "parts": [{"text": f"{message['content']}"}]})
        elif message["role"] == "assistant":
            gemini_history.append({"role": "model", "parts": [{"text": f"{message['content']}"}]})
    return gemini_history

if __name__ == "__main__":
    pass