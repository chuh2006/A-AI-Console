import time
from google import genai
from typing import Generator, Dict, Any, List
from .llm_base import BaseLLMClient

class GeminiClient(BaseLLMClient):
    def _convert_history(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """将 OpenAI 格式历史转换为 Gemini 格式"""
        gemini_history = []
        for msg in messages:
            if msg["role"] == "system":
                # System prompt 会在后面通过特定方式或合并到第一条消息中处理，
                # 但根据你原来的 openai_to_gemini 逻辑，直接跳过了 system，这里保持一致
                sys_prompt = msg["content"]
                continue
            
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [{"text": str(msg['content'])}]})
        return gemini_history

    def chat_stream(self, messages: List[Dict[str, Any]], temperature: float, image_paths: List[str] = None, **kwargs) -> Generator[Dict[str, Any], None, None]:
        client = genai.Client(api_key=self.api_key)
        gemini_messages = self._convert_history(messages)

        # 1. 处理图片上传
        if image_paths:
            uploaded_files = []
            for i, img_path in enumerate(image_paths):
                # 抛出一条系统消息让 UI 渲染进度，取代原来硬编码的 print
                yield {"type": "system", "content": f"正在上传图片 {i+1}/{len(image_paths)}: {img_path}...\n"}
                file_obj = client.files.upload(file=img_path)
                uploaded_files.append({"file_data": {"file_uri": file_obj.uri, "mime_type": file_obj.mime_type}})
            
            # 将上传的文件追加到最后一条用户消息的 parts 中
            if gemini_messages and gemini_messages[-1]["role"] == "user":
                gemini_messages[-1]["parts"].extend(uploaded_files)

        # 2. 解析特有参数
        enable_search = kwargs.get("enable_search", False)
        
        # 兼容你原来的数字 0-3 输入转换
        think_level_input = str(kwargs.get("think_level", "2"))
        if self.model_name == "gemini-3.1-pro-preview" and think_level_input == "0":
            think_level_input = "1"
            
        think_level_mapping = {"0": "minimal", "1": "low", "2": "medium", "3": "high"}
        think_level = think_level_mapping.get(think_level_input, think_level_input) # 如果直接传了英文也能兼容

        tools = [{"google_search": {}}] if enable_search else None

        # 3. 发起请求
        response = client.models.generate_content_stream(
            model=self.model_name,
            contents=gemini_messages,
            config=genai.types.GenerateContentConfig(
                thinking_config=genai.types.ThinkingConfig(
                    include_thoughts=True,
                    thinking_level=think_level
                ),
                tools=tools
            )
        )

        thought_content = ""
        last_chunk = None
        begin_time = time.time()
        has_thought = False
        isThinking = False
        # 4. 处理流式返回
        for chunk in response:
            if chunk.candidates and chunk.candidates[0].content.parts:
                for part in chunk.candidates[0].content.parts:
                    if getattr(part, 'thought', False):
                        isThinking = True
                        has_thought = True
                        thought_content += part.text
                        yield {"type": "thinking", "content": part.text}
                    elif part.text:
                        if isThinking:
                            think_time = time.time() - begin_time
                            yield {"type": "meta", "thinking_time": think_time}
                            isThinking = False
                        yield {"type": "content", "content": part.text}
            last_chunk = chunk

        # 5. 流结束，提取 metadata (搜索链接和思考耗时)
        uris = []
        status = False
        tool_history = []
        if last_chunk and last_chunk.candidates and last_chunk.candidates[0].grounding_metadata:
            metadata = last_chunk.candidates[0].grounding_metadata
            if metadata.grounding_chunks:
                for chunk_data in metadata.grounding_chunks:
                    if getattr(chunk_data, 'web', None):
                        title = chunk_data.web.title
                        uri = chunk_data.web.uri
                        uris.append(f"- [{title}]({uri})")
                        status = True  # 只要有一个搜索结果就认为搜索成功了
        if status:
            tool_history.append({
                "name": "google_search",
                "status": "success",
            })

        yield {
            "type": "meta",
            "thinking_time": think_time if has_thought else -1.0,
            "uris": uris,
            "think_level": think_level,
            "tool_call_history": tool_history
        }