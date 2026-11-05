from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POLYFLOW_", env_file=".env", extra="ignore")

    env: str = "dev"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://polyflow:polyflow@localhost:5432/polyflow"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = ["http://localhost:3000"]
    readiness_timeout_s: float = 2.0
    piper_url: str = "http://localhost:5000"
    whisper_url: str = "http://localhost:9000"
    # Synthesized speech is cached here (a persistent volume in Compose).
    audio_cache_dir: str = "/data/audio"
    tts_timeout_s: float = 20.0
    # Whisper accepts up to 30 seconds of audio. CPU decoding plus a bounded queue can
    # legitimately take longer than that, so keep enough wall-clock budget for the work.
    stt_timeout_s: float = 120.0
    # A spoken answer is one word or a short phrase: refuse larger uploads before Whisper.
    speech_max_upload_bytes: int = 1024 * 1024

    # Local language model (AI tutor, generated stories): an OpenAI-compatible chat endpoint
    # such as Ollama (http://ollama:11434/v1) or llama.cpp server. Unset = no model; the tutor
    # then answers from the curriculum's own explanations. A host outside localhost/private
    # networks is refused unless llm_allow_remote is set: learner text must not leave the
    # house without an explicit decision.
    llm_url: str | None = None
    llm_model: str = "qwen2.5:7b-instruct"
    llm_api_key: str | None = None
    llm_timeout_s: float = 60.0
    llm_allow_remote: bool = False
    # Model text for child profiles only when explicitly enabled (it still has to pass the
    # content checks); otherwise children get the reviewed curriculum explanations.
    llm_for_children: bool = False

    # Build provenance, baked into the image at build time (see scripts/build-info.sh).
    git_sha: str = "unknown"
    git_branch: str = "unknown"
    build_time: str | None = None

    # Auth. Set POLYFLOW_COOKIE_SECURE=true whenever the app is served over HTTPS.
    cookie_secure: bool = False
    session_cookie_name: str = "pf_session"
    session_ttl_days: int = 30
    login_max_attempts: int = 5  # per username within the window
    login_max_attempts_per_ip: int = 30
    login_window_s: int = 900
    default_timezone: str = "Europe/Prague"


@lru_cache
def get_settings() -> Settings:
    return Settings()
