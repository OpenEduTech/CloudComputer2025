from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    app_env: str = "dev"
    app_debug: bool = True

    redis_url: str = "redis://localhost:6379/0"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j_password"

    llm_provider: str = "openai_compat"  # mock | openai_compat
    openai_base_url: str | None = None
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.2"

    enable_wiki: bool = False
    enable_arxiv: bool = False
    local_kb_path: str = "/app/kb"


settings = Settings()

