from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://labellens:labellens@localhost:5432/labellens"
    ollama_url: str = "http://localhost:11434/api/generate"
    ollama_model: str = "gemma2:2b"
    ocr_engine: str = "tesseract"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
