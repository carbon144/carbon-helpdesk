from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Carbon Expert Hub"
    VERSION: str = "1.0.0"

    DATABASE_URL: str = ""  # REQUIRED: set via .env or environment variable
    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET: str = ""  # REQUIRED: set via .env or environment variable

    ENVIRONMENT: str = "development"  # "development" or "production"

    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480  # 8 hours

    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    ANTHROPIC_API_KEY: str = ""
    GMAIL_CLIENT_ID: str = ""
    GMAIL_CLIENT_SECRET: str = ""
    GMAIL_REDIRECT_URI: str = "http://localhost:8000/api/gmail/callback"
    GMAIL_SUPPORT_EMAIL: str = ""
    GMAIL_REFRESH_TOKEN: str = ""

    SLACK_BOT_TOKEN: str = ""
    SLACK_SIGNING_SECRET: str = ""
    SLACK_SUPPORT_CHANNEL: str = ""

    # Meta (WhatsApp, Instagram, Facebook)
    META_APP_SECRET: str = ""
    META_VERIFY_TOKEN: str = ""
    META_PAGE_ACCESS_TOKEN: str = ""
    META_WHATSAPP_TOKEN: str = ""
    META_WHATSAPP_PHONE_ID: str = ""
    META_PAGE_ID: str = ""
    META_INSTAGRAM_ACCOUNT_ID: str = ""

    SHOPIFY_STORE: str = ""  # ex: carbon-smartwatch.myshopify.com
    SHOPIFY_ACCESS_TOKEN: str = ""  # Admin API access token

    YAMPI_TOKEN: str = ""  # Yampi API token
    YAMPI_ALIAS: str = ""  # Yampi store alias

    APPMAX_API_KEY: str = ""  # Appmax API key

    GOOGLE_SERVICE_ACCOUNT_JSON: str = ""  # JSON string of service account credentials
    GOOGLE_DRIVE_FOLDER_ID: str = ""  # Optional: folder to upload files to

    LINKETRACK_USER: str = ""
    LINKETRACK_TOKEN: str = ""
    TRACK17_API_KEY: str = ""

    NOTION_TOKEN: str = ""
    NOTION_DATABASE_ID: str = ""  # Auto-created if empty

    SLA_URGENT_HOURS: int = 4
    SLA_HIGH_HOURS: int = 8
    SLA_MEDIUM_HOURS: int = 24
    SLA_LOW_HOURS: int = 48

    class Config:
        env_file = ".env"


settings = Settings()


def validate_settings():
    """Log warnings for missing critical settings on startup."""
    import logging
    logger = logging.getLogger(__name__)

    if not settings.DATABASE_URL:
        logger.critical("DATABASE_URL is not set! Application will not work.")
    if not settings.JWT_SECRET:
        logger.critical("JWT_SECRET is not set! Authentication will not work.")
    if settings.JWT_SECRET and len(settings.JWT_SECRET) < 32:
        logger.warning("JWT_SECRET is short. Use at least 32 characters for security.")
    if not settings.ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set. AI features will be disabled.")
    if not settings.GMAIL_REFRESH_TOKEN:
        logger.warning("GMAIL_REFRESH_TOKEN not set. Email integration disabled.")


validate_settings()
