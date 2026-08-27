from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://labellens:labellens@localhost:5432/labellens"
    ollama_url: str = "http://localhost:11434/api/generate"
    ollama_model: str = "gemma2:2b"
    ocr_engine: str = "paddleocr"

    # LLM 요약 생성 provider — "gemma"(Ollama, 기존) 또는 "vllm"(OpenAI 호환 서버).
    # scripts/generate_compare.py의 call_llm()이 이 값으로 call_ollama/call_vllm을 고른다.
    llm_provider: str = "gemma"
    vllm_base_url: str = "http://localhost:8000/v1"
    vllm_model: str = "Qwen/Qwen3-8B-AWQ"

    # JWT 서명 키 (app/auth.py). 로컬 개발용 기본값 — 실제 배포 환경에서는 반드시
    # .env의 SECRET_KEY로 무작위 값을 덮어써야 한다.
    secret_key: str = "dev-only-insecure-secret-key"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
