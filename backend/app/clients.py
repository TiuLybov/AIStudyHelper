import base64
from typing import Any

import httpx
from openai import AsyncOpenAI

from app.config import settings

TUTOR_SYSTEM_PROMPT = (
    "Ты учебный AI-ассистент. Не решай задачу за ученика полностью с первого ответа. "
    "Дай краткую подсказку, объясни ход мысли, а в конце выдели финальный ответ отдельной строкой "
    "в формате 'Ответ: ...'."
)


class LlmGateway:
    def __init__(self) -> None:
        self._yandex_client = AsyncOpenAI(
            api_key=settings.yandex_api_key,
            base_url=settings.yandex_base_url,
            project=settings.yandex_project_id,
        )

    async def yandex_complete(
        self,
        question: str,
        system_prompt: str | None = None,
        context: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
        model_name: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        user_text = question
        prefix_parts: list[str] = []
        if system_prompt:
            prefix_parts.append(system_prompt)
        if context:
            prefix_parts.append(f"Контекст для решения:\n{context}")
        if prefix_parts:
            user_text = "\n\n".join(prefix_parts) + "\n\nВопрос:\n" + user_text

        if attachments:
            user_text += "\n\nДанные из приложенных файлов:\n"
            for item in attachments:
                user_text += f"- {item['filename']} ({item['size_bytes']} bytes, base64):\n{item['content_b64'][:4000]}\n"

        request_kwargs: dict[str, Any] = {
            "input": user_text,
            "temperature": settings.default_temperature,
            "max_output_tokens": settings.default_max_tokens,
        }
        if settings.yandex_prompt_id:
            request_kwargs["prompt"] = {"id": settings.yandex_prompt_id}
        selected_model = model_name or settings.yandex_model
        if selected_model:
            request_kwargs["model"] = selected_model
        if "prompt" not in request_kwargs and "model" not in request_kwargs:
            raise RuntimeError("Set YANDEX_PROMPT_ID or YANDEX_MODEL in backend/.env")

        response = await self._yandex_client.responses.create(**request_kwargs)
        text = response.output_text or ""
        usage = response.usage.model_dump() if response.usage else {}
        return text, {
            "provider": "yandex_openai_compat",
            "usage": usage,
            "model": selected_model,
            "prompt_id": settings.yandex_prompt_id or None,
        }

    async def local_finetuned_complete(
        self,
        question: str,
        attachments: list[dict[str, Any]] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        payload: dict[str, Any] = {"question": question}
        if attachments:
            payload["attachments"] = attachments
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(settings.local_finetuned_endpoint, json=payload)
            response.raise_for_status()
            data = response.json()
        return data["answer"], {"provider": "local_finetuned", "raw": data.get("metadata", {})}


def bytes_to_attachment(filename: str, content: bytes) -> dict[str, Any]:
    return {
        "filename": filename,
        "size_bytes": len(content),
        "content_b64": base64.b64encode(content).decode("ascii"),
    }
