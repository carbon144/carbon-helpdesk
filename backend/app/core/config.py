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
