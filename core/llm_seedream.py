import base64
import mimetypes
import pathlib
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx
from volcenginesdkarkruntime import Ark
from volcenginesdkarkruntime.types.images import ContentGenerationTool, SequentialImageGenerationOptions


IMAGE_MODELS = {
    "doubao-seedream-5-0-260128",
    "doubao-seedream-4-5-251128",
}
IMAGE_REF_LIMIT = 14
IMAGE_TOTAL_LIMIT = 15


@dataclass
class SeedreamImageJob:
    id: str
    model: str
    prompt: str
    requested_count: int
    size: str
    status: str = "queued"
    generated_paths: list[str] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""
    submitted: threading.Event = field(default_factory=threading.Event)
    done: threading.Event = field(default_factory=threading.Event)


def normalize_seedream_model(value: Any) -> str:
    model = str(value or "").strip()
    return model if model in IMAGE_MODELS else "doubao-seedream-5-0-260128"


def normalize_seedream_size(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "2K"

    upper_value = raw.upper()
    if upper_value in {"1K", "2K", "3K", "4K"}:
        return upper_value

    normalized = raw.lower().replace("×", "x").replace("脳", "x").replace("*", "x").replace(" ", "")
    if normalized.count("x") == 1:
        left, right = normalized.split("x", 1)
        if left.isdigit() and right.isdigit():
            return f"{int(left)}x{int(right)}"

    return "2K"


def normalize_seedream_image_count(value: Any, reference_count: int = 0) -> int:
    try:
        count = int(str(value or "1").strip())
    except (TypeError, ValueError):
        count = 1
    remaining_budget = IMAGE_TOTAL_LIMIT - max(0, int(reference_count or 0))
    if remaining_budget <= 0:
        return 0
    return max(1, min(count, remaining_budget))


class SeedreamImageGenerator:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://ark.cn-beijing.volces.com/api/v3",
        project_root: str | pathlib.Path | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.project_root = pathlib.Path(project_root or pathlib.Path(__file__).resolve().parent.parent)

    def start(
        self,
        *,
        prompt: str,
        model: str,
        image_paths: list[str] | None = None,
        size: str = "2K",
        count: int = 1,
        enable_search: bool = False,
        output_format: str = "jpeg",
    ) -> SeedreamImageJob:
        clean_prompt = str(prompt or "").strip()
        if not clean_prompt:
            raise ValueError("image_gen 工具缺少生图提示词。")
        if not self.api_key:
            raise ValueError("缺少 doubao API key，无法调用 Seedream。")

        ref_paths = list(image_paths or [])[:IMAGE_REF_LIMIT]
        requested_count = normalize_seedream_image_count(count, len(ref_paths))
        if requested_count <= 0:
            raise ValueError("当前参考图数量已达到上限，无法继续生成新图片。")

        job = SeedreamImageJob(
            id=uuid.uuid4().hex,
            model=normalize_seedream_model(model),
            prompt=clean_prompt,
            requested_count=requested_count,
            size=normalize_seedream_size(size),
        )
        worker = threading.Thread(
            target=self._run_job,
            name=f"seedream-image-{job.id[:8]}",
            args=(job,),
            kwargs={
                "image_paths": ref_paths,
                "enable_search": bool(enable_search),
                "output_format": self._normalize_output_format(output_format),
            },
            daemon=True,
        )
        worker.start()
        return job

    def _run_job(
        self,
        job: SeedreamImageJob,
        *,
        image_paths: list[str],
        enable_search: bool,
        output_format: str,
    ) -> None:
        client = Ark(base_url=self.base_url, api_key=self.api_key)
        job.status = "running"
        try:
            request_kwargs = self._build_request_kwargs(
                job=job,
                image_paths=image_paths,
                enable_search=enable_search,
                output_format=output_format,
            )
            completed_indices: set[int] = set()
            response_error_message = ""
            with client.images.generate(**request_kwargs) as response:
                job.submitted.set()
                for event in response:
                    event_error = getattr(event, "error", None)
                    event_error_message = str(getattr(event_error, "message", "") or "").strip()
                    if not hasattr(event, "image_index"):
                        response_error_message = event_error_message or response_error_message
                        continue

                    try:
                        item_index = int(getattr(event, "image_index", len(completed_indices)) or 0)
                    except (TypeError, ValueError):
                        item_index = len(completed_indices)
                    if item_index in completed_indices:
                        continue

                    item_url = str(getattr(event, "url", "") or "").strip()
                    item_b64 = str(getattr(event, "b64_json", "") or "").strip()
                    if event_error_message and not item_url and not item_b64:
                        completed_indices.add(item_index)
                        job.failures.append({"index": item_index, "error": event_error_message})
                        continue
                    if not item_url and not item_b64:
                        continue

                    try:
                        saved_path = self._save_generated_image(
                            image_index=item_index,
                            url=item_url,
                            b64_json=item_b64,
                            requested_output_format=output_format,
                        )
                        completed_indices.add(item_index)
                        job.generated_paths.append(saved_path)
                    except Exception as exc:
                        completed_indices.add(item_index)
                        job.failures.append({"index": item_index, "error": str(exc)})

            if job.generated_paths:
                job.status = "completed"
            else:
                job.status = "failed"
                job.error = response_error_message or "Seedream 没有返回可保存的图片。"
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            job.submitted.set()
        finally:
            job.done.set()
            client.close()

    def _build_request_kwargs(
        self,
        *,
        job: SeedreamImageJob,
        image_paths: list[str],
        enable_search: bool,
        output_format: str,
    ) -> dict[str, Any]:
        image_payload: str | list[str] | None = None
        if image_paths:
            encoded_images = [self._local_image_to_data_url(path) for path in image_paths]
            image_payload = encoded_images[0] if len(encoded_images) == 1 else encoded_images

        request_kwargs: dict[str, Any] = {
            "model": job.model,
            "prompt": job.prompt,
            "image": image_payload,
            "response_format": "url",
            "size": job.size,
            "watermark": False,
            "stream": True,
        }
        if enable_search:
            request_kwargs["tools"] = [ContentGenerationTool(type="web_search")]
        if job.model == "doubao-seedream-5-0-260128":
            request_kwargs["output_format"] = output_format
        if job.requested_count > 1:
            request_kwargs["sequential_image_generation"] = "auto"
            request_kwargs["sequential_image_generation_options"] = SequentialImageGenerationOptions(
                max_images=job.requested_count
            )
        return request_kwargs

    def _get_generated_image_dir(self) -> pathlib.Path:
        image_dir = self.project_root / "chat_result" / "generate" / time.strftime("%Y-%m-%d")
        image_dir.mkdir(parents=True, exist_ok=True)
        return image_dir

    def _generate_unique_image_name(self, extension: str) -> str:
        ext = (extension or ".png").lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        return f"generate_{uuid.uuid4().hex}{ext}"

    def _local_image_to_data_url(self, path: str) -> str:
        mime_type, _ = mimetypes.guess_type(path)
        mime_type = mime_type or "image/png"
        with open(path, "rb") as handle:
            encoded = base64.b64encode(handle.read()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    def _download_image_asset(self, url: str) -> tuple[bytes, str]:
        response = httpx.get(url, timeout=120.0, follow_redirects=True)
        response.raise_for_status()
        return response.content, response.headers.get("content-type", "")

    def _save_generated_image(
        self,
        *,
        image_index: int,
        url: str,
        b64_json: str,
        requested_output_format: str,
    ) -> str:
        mime_type = ""
        binary = b""

        if url:
            binary, mime_type = self._download_image_asset(url)
        elif b64_json:
            binary = base64.b64decode(b64_json)

        if not binary:
            raise ValueError(f"第 {image_index + 1} 张图片没有返回可保存的数据。")

        extension = ""
        if requested_output_format in {"png", "jpeg", "jpg", "webp"}:
            extension = ".jpg" if requested_output_format == "jpg" else f".{requested_output_format}"
        elif mime_type:
            extension = mimetypes.guess_extension(mime_type.split(";", 1)[0].strip()) or ""
        if not extension:
            extension = ".jpeg"

        target_path = self._get_generated_image_dir() / self._generate_unique_image_name(extension)
        with open(target_path, "wb") as handle:
            handle.write(binary)
        return str(target_path)

    def _normalize_output_format(self, value: Any) -> str:
        output_format = str(value or "jpeg").strip().lower()
        return output_format if output_format in {"jpeg", "png", "webp"} else "jpeg"
