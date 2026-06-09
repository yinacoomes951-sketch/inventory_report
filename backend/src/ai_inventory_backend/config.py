from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(default="", alias="AI_INVENTORY_DATABASE_URL")
    ai_model: str = Field(default="gpt-4.1-mini", alias="AI_INVENTORY_MODEL")
    use_mock_data: bool = Field(default=True, alias="AI_INVENTORY_USE_MOCK_DATA")
    llm_enabled: bool = Field(default=False, alias="AI_INVENTORY_LLM_ENABLED")
    llm_api_key: str = Field(default="", alias="AI_INVENTORY_LLM_API_KEY")
    llm_base_url: str = Field(default="https://api.deepseek.com", alias="AI_INVENTORY_LLM_BASE_URL")
    llm_model: str = Field(default="deepseek-chat", alias="AI_INVENTORY_LLM_MODEL")
    llm_timeout_seconds: int = Field(default=60, alias="AI_INVENTORY_LLM_TIMEOUT_SECONDS")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
