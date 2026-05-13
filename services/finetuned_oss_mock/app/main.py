from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Finetuned OSS Mock", version="0.1.0")


class GenerateRequest(BaseModel):
    question: str = Field(min_length=1)
    attachments: list[dict] = Field(default_factory=list)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/generate")
async def generate(request: GenerateRequest) -> dict:
    hint = "Сначала выдели известные данные и запиши формулу."
    if request.attachments:
        hint = "Сначала изучи данные из файла, выдели ключевые значения и проверь единицы измерения."
    answer = (
        f"{hint}\n"
        "Промежуточное рассуждение: ...\n"
        "Ответ: [mock-finetuned-output]"
    )
    return {"answer": answer, "metadata": {"model": "qwen2.5-7b-lora-mock", "attachments": len(request.attachments)}}
