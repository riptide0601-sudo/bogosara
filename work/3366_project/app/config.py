from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://labellens:labellens@localhost:5432/labellens"
    ollama_url: str = "http://localhost:11434/api/generate"
    ollama_model: str = "gemma2:2b"
    ocr_engine: str = "paddleocr"
    # JWT 서명 키 (app/auth.py). 로컬 개발용 기본값 — 실제 배포 환경에서는 반드시
    # .env의 SECRET_KEY로 무작위 값을 덮어써야 한다.
    secret_key: str = "dev-only-insecure-secret-key"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
