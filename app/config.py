import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or .env file."""

    BOT_TOKEN: str = Field(
        default=os.environ.get("BOT_TOKEN", "8943083272:AAHr8eRczMwlh9AkDGQc7Vbzb6zJbsgSeRU"),
        description="Telegram Bot Token from @BotFather"
    )
    DATABASE_URL: str = Field(
        default=f"sqlite+aiosqlite:///{BASE_DIR / 'jobhunter.db'}",
        description="Async database connection string",
    )
    DIGEST_TIME: str = Field(default="09:00", description="Daily digest delivery time (HH:MM)")
    SCRAPE_INTERVAL_HOURS: int = Field(default=4, description="Scraping frequency in hours")
    MATCH_THRESHOLD: int = Field(default=60, description="Minimum matching score (0-100) to recommend")
    OPENAI_API_KEY: str = Field(default="", description="Optional OpenAI API key for advanced matching")

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
