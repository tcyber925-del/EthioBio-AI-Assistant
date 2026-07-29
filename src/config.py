from typing import Optional

from pydantic_settings import BaseSettings


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
    ollama_api_key: Optional[str] = None  # Ollama Cloud (https://ollama.com)

    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_default_model: str = "openai/gpt-4o"

    fallback_provider: Optional[str] = None
    fallback_api_key: Optional[str] = None
    fallback_model: Optional[str] = None

    provider_openai_compatible_url: Optional[str] = None
    provider_openai_compatible_api_key: Optional[str] = None
    provider_openai_compatible_model: Optional[str] = None
    provider_openai_compatible_name: Optional[str] = None

    vector_store_path: str = "./data/vectors_new"
    collection_name: str = "ethiobio_curriculum"
    store_backend: str = "pgvector"  # always pgvector

    gemini_api_key: str = ""
    groq_api_key: str = ""
    azure_speech_key: str = ""
    azure_speech_region: str = ""
    whisper_model: str = "base"

    dashboard_url: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"

    cloudflare_account_id: str = ""
    cloudflare_api_token: str = ""
    cloudflare_image_model: str = "@cf/black-forest-labs/flux-1-schnell"

    email_host: str = ""
    email_port: int = 587
    email_user: str = ""
    email_password: str = ""
    email_from: str = "noreply@ethiobio.com"
    email_use_tls: bool = True
    jwt_secret: str = "change-me-jwt-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    internal_api_key: str = ""

    # Guardrail settings
    rate_limit_enabled: bool = True
    rate_limit_user_max: int = 60
    rate_limit_user_window: int = 60
    rate_limit_ip_max: int = 120
    rate_limit_ip_window: int = 60
    rate_limit_global_max: int = 1000
    rate_limit_global_window: int = 60

    input_sanitize_enabled: bool = True
    input_max_length: int = 2000

    prompt_injection_enabled: bool = True
    prompt_injection_threshold: float = 0.7

    output_toxicity_enabled: bool = True
    output_pii_detection_enabled: bool = True
    output_topic_enforcement_enabled: bool = True

    tool_guard_enabled: bool = True

    drift_monitor_enabled: bool = True
    drift_monitor_window: int = 1000
    drift_alert_threshold: float = 0.05

    # Observability settings
    otel_service_name: str = "ethiobio"
    otel_endpoint: Optional[str] = None
    otel_traces_sampling_rate: float = 1.0
    sentry_dsn: Optional[str] = None  # Sentry free tier (https://sentry.io)

    observability_metrics_enabled: bool = True
    observability_health_enabled: bool = True
    observability_alerting_enabled: bool = True

    eval_enabled: bool = True
    eval_sampling_rate: float = 0.15
    eval_judge_model: str = "gpt-4o-mini"
    eval_drift_threshold: float = 0.10

    telegram_voice_max_size: int = 20_971_520  # 20 MB (Telegram voice file limit)
    audio_storage_path: str = "./data/audio_recordings"
    audio_retention_days: int = 90

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


settings = Settings()
