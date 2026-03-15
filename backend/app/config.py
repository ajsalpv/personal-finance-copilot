"""
Nova AI Life Assistant — Configuration
"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Callista AI Assistant"
    DEBUG: bool = True

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    DATABASE_URL: str = ""

    # JWT Auth
    JWT_SECRET: str = "change-this-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440  # 24 hours

    # AES-256 Encryption
    AES_KEY: str = ""

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    OWNER_TELEGRAM_ID: str = ""

    # AI APIs
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # Voice Auth
    VOICE_SIMILARITY_THRESHOLD: float = 0.85

    # Storage
    STORAGE_BUCKET: str = "user-files"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


def get_settings() -> Settings:
    from dotenv import load_dotenv
    load_dotenv(override=True)
    return Settings()
