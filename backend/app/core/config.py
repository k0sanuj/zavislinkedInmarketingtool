"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Zavis LinkedIn Marketing Tool"
    SECRET_KEY: str = "change-me-to-a-random-secret"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/zavis_linkedin"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/zavis_linkedin"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Google Sheets (service account — legacy, optional)
    GOOGLE_CREDENTIALS_JSON: str = "credentials.json"

    # Google OAuth 2.0 (user-based auth via browser)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/google/callback"

    # LinkedIn cookies (Sales Navigator auth)
    LINKEDIN_LI_AT_COOKIE: str = ""
    LINKEDIN_JSESSIONID_COOKIE: str = ""

    # AI
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # Scraping behavior
    MAX_EMPLOYEES_PER_COMPANY: int = 30
    MAX_COMPANIES_PER_LAUNCH: int = 50
    SCRAPE_DELAY_MIN_SECONDS: int = 2
    SCRAPE_DELAY_MAX_SECONDS: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
