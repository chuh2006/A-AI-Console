from __future__ import annotations
import concurrent.futures
import json
import re
from typing import Any, Dict, Generator, List, Tuple
from .llm_base import BaseLLMClient
from .llm_openai import OpenAICompatibleClient
from tools.prompts import Prompts

class MultiAssistant(BaseLLMClient):
    """
    一个多助理集群，通过多个LLM多次协作来完成对用户的请求。每个LLM都是一个独立的助手，可以有不同的角色和专长。
    """
    DEFAULT_PROVIDER_ORDER: Tuple[str, ...] = ("deepseek", "qwen", "doubao", "kimi")
    DEFAULT_BASE_URLS: Dict[str, str] = {
        "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "doubao": "https://ark.cn-beijing.volces.com/api/v3",
        "deepseek": "https://api.deepseek.com",
        "kimi": "https://api.moonshot.cn/v1",
    }
    DEFAULT_MODEL_MAP: Dict[str, Dict[str, str]] = {
        "deepseek": {
            "planner": "deepseek-reasoner",
            "worker": "deepseek-chat",
            "integrator": "deepseek-reasoner",
        },
        "qwen": {
            "planner": "qwen3.5-plus",
            "worker": "qwen3.5-plus",
            "integrator": "qwen3.5-plus",
        },
        "doubao": {
            "planner": "doubao-seed-2-0-pro-260215",
            "worker": "doubao-seed-2-0-pro-260215",
            "integrator": "doubao-seed-2-0-pro-260215",
        },
        "kimi": {
            "planner": "kimi-k2.5",
            "worker": "kimi-k2.5",
            "integrator": "kimi-k2.5",
        },
    }

    def __init__(self, api_keys: dict[str, str] | list[str], model_name: str, base_urls: dict | None = None, model_map: dict | None = None):
        super().__init__(api_key="", model_name=model_name, base_url="")

        self.api_keys = self._normalize_api_keys(api_keys)
        self.base_urls = {**self.DEFAULT_BASE_URLS, **(base_urls or {})}
        self.model_map = self._build_model_map(model_map)
        self.providers = [provider for provider in self.DEFAULT_PROVIDER_ORDER if self.api_keys.get(provider)]
        self._round_robin_index = 0

    def _normalize_api_keys(self, api_keys: dict[str, str] | list[str]) -> Dict[str, str]:
        if isinstance(api_keys, dict):
            return {k: v for k, v in api_keys.items() if isinstance(v, str) and v.strip()}

        # 兼容旧构造方式：按固定顺序把列表映射到 provider。
        mapped: Dict[str, str] = {}
        for idx, provider in enumerate(self.DEFAULT_PROVIDER_ORDER):
            if idx < len(api_keys) and isinstance(api_keys[idx], str) and api_keys[idx].strip():
                mapped[provider] = api_keys[idx]
        return mapped

    def _build_model_map(self, model_map: dict | None) -> Dict[str, Dict[str, str]]:
        merged = {provider: stage_map.copy() for provider, stage_map in self.DEFAULT_MODEL_MAP.items()}
        if not model_map:
            return merged

        for provider, stage_map in model_map.items():
            if provider not in merged or not isinstance(stage_map, dict):
                continue
            for stage_name in ("planner", "worker", "integrator"):
                if isinstance(stage_map.get(stage_name), str) and stage_map[stage_name].strip():
                    merged[provider][stage_name] = stage_map[stage_name].strip()
        return merged

    def _pick_provider(self, prefer: str | None = None) -> str:
        if prefer and prefer in self.providers:
            return prefer
        if not self.providers:
            raise RuntimeError("multi-assistant 未配置可用的 API Key（支持 deepseek/qwen/doubao/kimi）。")
        return self.providers[0]

    def _next_provider(self) -> str:
        if not self.providers:
            raise RuntimeError("multi-assistant 未配置可用的 API Key（支持 deepseek/qwen/doubao/kimi）。")
        provider = self.providers[self._round_robin_index % len(self.providers)]
        self._round_robin_index += 1
        return provider

    def _create_client(self, provider: str, stage: str) -> OpenAICompatibleClient:
        model_name = self.model_map.get(provider, {}).get(stage)
        if not model_name:
            raise RuntimeError(f"未找到 provider={provider} stage={stage} 对应的模型配置")

        return OpenAICompatibleClient(
            api_key=self.api_keys[provider],
            model_name=model_name,
            base_url=self.base_urls.get(provider, ""),
        )

    def _get_last_user_text(self, messages: List[Dict[str, str]]) -> str:
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    return content
        return ""

    def _collect_response(self, client: OpenAICompatibleClient, context: List[Dict[str, str]], temperature: float) -> tuple[str, str, Dict[str, Any]]:
        content = ""
        thinking = ""
        meta: Dict[str, Any] = {}
        for chunk in client.chat_stream(messages=context, temperature=temperature):
            chunk_type = chunk.get("type")
            if chunk_type == "content":
                content += chunk.get("content", "")
            elif chunk_type == "thinking":
                thinking += chunk.get("content", "")
            elif chunk_type == "meta":
                meta.update(chunk)
        return content.strip(), thinking, meta

    def _extract_json_payload(self, text: str) -> Dict[str, Any]:
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except Exception:
            pass

        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return {}
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _plan_tasks(self, user_input: str, temperature: float) -> tuple[list[str], int, str, str]:
        planner_provider = self._pick_provider(prefer="deepseek")
        planner_client = self._create_client(planner_provider, stage="planner")

        planner_context = [
            {"role": "system", "content": Prompts.first_prompt},
            {"role": "user", "content": user_input},
        ]
        planner_answer, planner_thinking, _ = self._collect_response(planner_client, planner_context, min(0.9, max(0.1, temperature)))

        payload = self._extract_json_payload(planner_answer)
        task_type = 1
        task_type_raw = str(payload.get("task_type", "并行完成"))
        if "递进" in task_type_raw:
            task_type = 2

        sub_tasks = payload.get("sub_tasks", [])
        prompts: list[str] = []
        if isinstance(sub_tasks, list):
            for item in sub_tasks:
                if isinstance(item, dict):
                    prompt_text = str(item.get("sub_task_prompt", "")).strip()
                    if prompt_text:
                        prompts.append(prompt_text)

        # 解析失败时退化为单任务直答，保证流程可继续。
        if not prompts:
            prompts = [user_input]
            task_type = 1

        return prompts, task_type, planner_answer, planner_thinking

    def _run_single_subtask(self, prompt: str, temperature: float, provider: str, sub_context: list[dict] | None = None) -> str:
        worker_client = self._create_client(provider, stage="worker")
        context: list[dict] = []
        if sub_context is not None:
            context.extend(sub_context)
            context.append({"role": "user", "content": prompt})
        else:
            context.extend([
                {"role": "system", "content": Prompts.parallel_sub_task_prompt},
                {"role": "user", "content": prompt},
            ])

        answer, _, _ = self._collect_response(worker_client, context, min(1.2, max(0.1, temperature + 0.2)))
        return answer if answer else "子任务未返回有效内容。"

    def _run_parallel_subtasks(self, prompts: list[str], temperature: float) -> list[str]:
        results = ["" for _ in prompts]
        max_workers = min(6, max(1, len(prompts)))

        def _worker(idx: int, prompt: str) -> tuple[int, str]:
            provider = self.providers[idx % len(self.providers)]
            try:
                return idx, self._run_single_subtask(prompt, temperature, provider=provider)
            except Exception as e:
                return idx, f"子任务执行失败：{e}"

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {executor.submit(_worker, idx, prompt): idx for idx, prompt in enumerate(prompts)}
            for future in concurrent.futures.as_completed(future_map):
                idx, answer = future.result()
                results[idx] = answer
        return results

    def _run_progressive_subtasks(self, prompts: list[str], temperature: float) -> list[str]:
        results: list[str] = []
        for idx, prompt in enumerate(prompts):
            progressive_context: list[dict] = [{"role": "system", "content": Prompts.progressive_task_prompt}]
            for i, answer in enumerate(results):
                progressive_context.append({"role": "user", "content": f"这是上游任务 {i+1} 的回答：{answer}"})
                progressive_context.append({"role": "assistant", "content": f"已收到上游任务 {i+1} 的回答。"})

            provider = self.providers[idx % len(self.providers)]
            answer = self._run_single_subtask(prompt, temperature, provider=provider, sub_context=progressive_context)
            results.append(answer)
        return results

    def _build_final_context(self, user_input: str, task_type: int, sub_task_answers: list[str]) -> list[dict]:
        final_context = [
            {"role": "system", "content": Prompts.getSummeryPrompt(False)},
            {"role": "user", "content": f"这是用户的原始请求：{user_input}"},
            {"role": "assistant", "content": "已收到用户的原始请求。"},
        ]

        if task_type == 1:
            final_context.append({"role": "user", "content": "子任务的完成逻辑是并行完成，各子任务相互独立。"})
        else:
            final_context.append({"role": "user", "content": "子任务的完成逻辑是递进完成，后一个子任务需要前一个子任务的结果。"})
        final_context.append({"role": "assistant", "content": "已确认子任务的完成逻辑。"})

        for i, answer in enumerate(sub_task_answers):
            final_context.append({"role": "user", "content": answer})
            final_context.append({"role": "assistant", "content": f"已收到第{i+1}个子任务的回答。"})

        final_context.append({"role": "user", "content": "你已经收到了所有子任务的回答，请根据这些回答整合出一个连贯且有条理的最终回复，确保内容准确且详尽。"})
        return final_context

    def chat_stream(self, messages: List[Dict[str, str]], temperature: float, **kwargs) -> Generator[Dict[str, Any], None, None]:
        try:
            user_input = self._get_last_user_text(messages)
            if not user_input:
                yield {"type": "content", "content": "未找到可处理的用户输入。"}
                return

            yield {"type": "system", "content": "[multi-assistant] 正在解析任务并规划子任务...\n"}
            sub_task_prompts, task_type, _, _ = self._plan_tasks(user_input, temperature)
            yield {"type": "system", "content": f"[multi-assistant] 任务拆解完成，共 {len(sub_task_prompts)} 个子任务。\n"}

            if task_type == 1:
                yield {"type": "system", "content": "[multi-assistant] 采用并行模式处理子任务。\n"}
                sub_task_answers = self._run_parallel_subtasks(sub_task_prompts, temperature)
            else:
                yield {"type": "system", "content": "[multi-assistant] 采用递进模式处理子任务。\n"}
                sub_task_answers = self._run_progressive_subtasks(sub_task_prompts, temperature)

            yield {"type": "system", "content": "[multi-assistant] 子任务完成，正在整合最终答案...\n"}
            final_context = self._build_final_context(user_input, task_type, sub_task_answers)

            integrator_provider = self._pick_provider(prefer="deepseek")
            integrator_client = self._create_client(integrator_provider, stage="integrator")
            for chunk in integrator_client.chat_stream(messages=final_context, temperature=temperature, **kwargs):
                yield chunk
        except Exception as e:
            yield {"type": "content", "content": f"multi-assistant 执行失败：{e}"}

    
