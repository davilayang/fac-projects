from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR: Path = Path(__file__).parent.parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # [AI]
    openai_key: SecretStr
    anthropic_api_key: SecretStr
    hf_token: SecretStr

    # [Database]
    db_database: str
    db_host: str = "localhost"
    db_port: int = 5050
    db_username: str
    db_password: SecretStr

    # [Defaults]
    data_dir: Path = ROOT_DIR / "data"
    embedding_model: str = "text-embedding-3-small"
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-12-v2"
    llm_model: str = "claude-sonnet-4-6"
    max_tokens: int = 1024
    rerank_cache_dir: str = "/tmp"
    sql_echo: bool = False
    log_level: str = "INFO"

    # [Auth]
    github_client_id: str = ""
    github_client_secret: SecretStr = SecretStr("")
    session_secret: SecretStr = SecretStr("change-me-in-production")
    allowed_emails: str = ""  # comma-separated; empty = any GitHub user
    allowed_github_org: str = ""  # org membership check; empty = skip
    cookie_secure: bool = False  # set True behind HTTPS

    # [S3]
    s3_access_key: SecretStr
    s3_secret_key: SecretStr
    s3_bucket_name: str = "vertuvian"

    @property
    def allowed_emails_set(self) -> set[str]:
        if not self.allowed_emails:
            return set()
        return {e.strip().lower() for e in self.allowed_emails.split(",") if e.strip()}

    @property
    def db_url(self) -> str:
        password = self.db_password.get_secret_value()
        return f"postgresql+psycopg://{self.db_username}:{password}@{self.db_host}:{self.db_port}/{self.db_database}"


@lru_cache
def get_settings() -> Settings:
    return Settings.model_validate({})
