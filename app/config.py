from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llm_provider: str = "deepseek"

    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-v4"

    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "qwen2.5:32b"

    tg_bot_token: str = ""

    database_path: str = "./data/langchain-git-ai.db"
    git_work_dir: str = "./repos"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()