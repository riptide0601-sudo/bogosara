from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/labellens.db"
    ollama_url: str = "http://localhost:11434/api/generate"
    ollama_model: str = "gemma2:2b"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
