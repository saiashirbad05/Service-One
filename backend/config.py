from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional, List

class Settings(BaseSettings):
    # Google Cloud / Vertex AI
    GCP_PROJECT_ID: str = Field(default="project-id")
    GCP_REGION: str = Field(default="region")
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    VERTEX_AI_PROJECT_ID: Optional[str] = None
    VERTEX_AI_LOCATION: Optional[str] = None

    # Agent Models
    AGENT_MODEL_FLASH_LITE: str = Field(default="gemini-2.5-flash-lite")
    AGENT_MODEL_FLASH: str = Field(default="gemini-2.5-flash")

    # Google Maps API
    GOOGLE_MAPS_API_KEY: Optional[str] = None

    # Web Scraper Config
    SCRAPER_ALLOWED_DOMAINS: str = Field(default="urbancompany.com,sulekha.com,justdial.com,nobroker.in")
    SCRAPER_MAX_CONCURRENCY: int = Field(default=3)
    SCRAPER_TIMEOUT_SECONDS: int = Field(default=10)
    SCRAPER_USER_AGENT: str = Field(default="Mozilla/5.0 (compatible; ServiceOneBot/1.0)")

    # Database Settings
    DATABASE_URL: str = Field(default="postgresql://postgres:Ommsai05@127.0.0.1:5432/postgres")
    CLOUD_SQL_INSTANCE_CONNECTION_NAME: Optional[str] = None
    DB_HOST: Optional[str] = None
    DB_PORT: Optional[int] = None
    DB_NAME: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None

    # Redis Cache
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    CACHE_TTL_SECONDS: int = Field(default=7200)

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    OAUTH_REDIRECT_URI: str = Field(default="http://localhost:8000/auth/google/callback")

    # Cloud Storage
    GCS_BUCKET_NAME: Optional[str] = None
    GCS_SIGNED_URL_EXPIRY_MINUTES: int = Field(default=15)

    # App Security
    JWT_SECRET_KEY: str = Field(default="key")
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_EXPIRE_MINUTES: int = Field(default=10080)

    # CORS
    FRONTEND_URL: str = Field(default="http://localhost:5173")
    ALLOWED_ORIGINS: Optional[str] = None

    # Rate Limiting
    RATE_LIMIT_QUOTE_CHECKS_PER_MINUTE: int = Field(default=10)
    RATE_LIMIT_REPORT_SUBMISSIONS_PER_HOUR: int = Field(default=5)

    # App Config
    APP_ENV: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
