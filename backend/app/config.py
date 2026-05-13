from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    yandex_api_key: str
    yandex_base_url: str = "https://ai.api.cloud.yandex.net/v1"
    yandex_project_id: str
    yandex_prompt_id: str = ""
    yandex_model: str = ""
    yandex_available_models: str = ""
    rag_kb_path: str = "../experiments/rag/knowledge_base.jsonl"
    local_finetuned_endpoint: str = "http://localhost:8010/generate"
    default_temperature: float = 0.2
    default_max_tokens: int = 256

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", case_sensitive=False)


settings = Settings()
