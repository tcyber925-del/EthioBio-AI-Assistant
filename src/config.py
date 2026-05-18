from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "EthioBio AI Assistant"
    debug: bool = False
    log_level: str = "INFO"
    secret_key: str = "change-me"

    database_url: str = "postgresql+asyncpg://ethiobio:ethiobio_pass@localhost:5432/ethiobio"
    database_sync_url: str = "postgresql://ethiobio:ethiobio_pass@localhost:5432/ethiobio"

    redis_url: str = "redis://localhost:6379/0"

    telegram_bot_token: str = ""
    telegram_webhook_url: Optional[str] = None
    telegram_webhook_secret: Optional[str] = None

    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "tinyllama"
    ollama_embed_model: str = "nomic-embed-text"

    fallback_provider: Optional[str] = None
    fallback_api_key: Optional[str] = None
    fallback_model: Optional[str] = None

    provider_openai_compatible_url: Optional[str] = None
    provider_openai_compatible_api_key: Optional[str] = None
    provider_openai_compatible_model: Optional[str] = None
    provider_openai_compatible_name: str = "lm-studio"

    vector_store_path: str = "./data/vectors_new"
    collection_name: str = "ethiobio_curriculum"

    whisper_model: str = "base"

    dashboard_url: str = "http://localhost:3000"
    jwt_secret: str = "change-me-jwt-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False}


settings = Settings()
