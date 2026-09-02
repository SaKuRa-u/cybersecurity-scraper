from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://scraper_user:password@postgres:5432/cybersec_scraper"
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:3000"
    SECRET_KEY: str = "change-me-to-random-string-at-least-32-chars"
    LOG_LEVEL: str = "INFO"

    GITHUB_TOKEN: str = ""
    MITRE_API_KEY: str = ""

    SCRAPER_CONCURRENT_REQUESTS: int = 5
    SCRAPER_RETRY_MAX: int = 3
    SCRAPER_RETRY_BACKOFF: int = 2

    EXPORT_DIR: str = "/app/exports"
    EXPORT_FORMAT: str = "jsonl"
    OPENSEARCH_INDEX_NAME: str = "cybersec_knowledge"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
