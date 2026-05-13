import re
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from app.clients import LlmGateway, TUTOR_SYSTEM_PROMPT, bytes_to_attachment
from app.config import settings
from app.rag import RagStore
from app.schemas import AskRequest, AskResponse, ModelVariant

app = FastAPI(title="AI Tutor Backend", version="0.1.0")
gateway = LlmGateway()
rag_store = RagStore(settings.rag_kb_path)


def is_probably_valid_model_uri(model_name: str) -> bool:
    return bool(re.match(r"^gpt://[^/]+/[^/]+/[^/]+$", model_name.strip()))


async def generate_answer(
    question: str,
    model_variant: ModelVariant,
    attachments: list[dict],
    model_name: str | None = None,
) -> AskResponse:
    if model_name and not is_probably_valid_model_uri(model_name):
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid model_name. Expected format: "
                "gpt://<project_id>/<model_name>/<version>, "
                "for example gpt://b1g5jloil44qmt951piv/yandexgpt/latest"
            ),
        )

    if model_variant == ModelVariant.baseline_gpt:
        answer, meta = await gateway.yandex_complete(
            question=question,
            attachments=attachments,
            model_name=model_name,
        )
        if not answer.strip():
            raise HTTPException(status_code=502, detail="Model returned empty answer. Check model_name URI.")
        return AskResponse(model_variant=model_variant, answer=answer, metadata=meta)

    if model_variant == ModelVariant.prompted_gpt:
        answer, meta = await gateway.yandex_complete(
            question=question,
            system_prompt=TUTOR_SYSTEM_PROMPT,
            attachments=attachments,
            model_name=model_name,
        )
        if not answer.strip():
            raise HTTPException(status_code=502, detail="Model returned empty answer. Check model_name URI.")
        return AskResponse(model_variant=model_variant, answer=answer, metadata=meta)

    if model_variant == ModelVariant.rag_gpt:
        docs = rag_store.retrieve(question, top_k=3)
        context = "\n\n".join([f"[{d.get('source', d.get('id', 'kb'))}] {d['text']}" for d in docs])
        answer, meta = await gateway.yandex_complete(
            question=question,
            system_prompt=TUTOR_SYSTEM_PROMPT,
            context=context,
            attachments=attachments,
            model_name=model_name,
        )
        if not answer.strip():
            raise HTTPException(status_code=502, detail="Model returned empty answer. Check model_name URI.")
        meta["retrieved_docs"] = docs
        return AskResponse(model_variant=model_variant, answer=answer, metadata=meta)

    if model_variant == ModelVariant.finetuned_oss:
        answer, meta = await gateway.local_finetuned_complete(question=question, attachments=attachments)
        return AskResponse(model_variant=model_variant, answer=answer, metadata=meta)

    raise HTTPException(status_code=400, detail=f"Unknown model variant: {model_variant}")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/models")
async def models() -> dict:
    models = [m.strip() for m in settings.yandex_available_models.split(",") if m.strip()]
    if settings.yandex_model and settings.yandex_model not in models:
        models.insert(0, settings.yandex_model)
    return {
        "default_model": settings.yandex_model,
        "models": models,
        "variants": [v.value for v in ModelVariant],
    }


@app.post("/ask-json", response_model=AskResponse)
async def ask_json(request: AskRequest) -> AskResponse:
    return await generate_answer(
        question=request.question,
        model_variant=request.model_variant,
        attachments=[],
        model_name=request.model_name,
    )


@app.post("/ask-file", response_model=AskResponse)
async def ask_file(
    question: Annotated[str, Form(...)],
    model_variant: Annotated[ModelVariant, Form(...)],
    model_name: Annotated[str | None, Form()] = None,
    files: list[UploadFile] = File(default=[]),
) -> AskResponse:
    attachments = []
    for f in files:
        content = await f.read()
        attachments.append(bytes_to_attachment(filename=f.filename or "file.bin", content=content))
    return await generate_answer(
        question=question,
        model_variant=model_variant,
        attachments=attachments,
        model_name=model_name,
    )
