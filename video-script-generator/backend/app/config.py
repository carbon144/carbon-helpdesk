from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://carbon:carbon@localhost:5433/video_scripts"

    # AI
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"

    # Helpdesk integration (Carbon Helpdesk API)
    HELPDESK_API_URL: str = "http://localhost:8000/api"
    HELPDESK_API_TOKEN: str = ""

    # Meta Ads integration
    META_ADS_ACCESS_TOKEN: str = ""
    META_ADS_ACCOUNT_ID: str = ""
    META_ADS_APP_SECRET: str = ""

    # Meta Ads Optimizer (internal tool) integration
    OPTIMIZER_API_URL: str = ""
    OPTIMIZER_API_TOKEN: str = ""

    # Auth
    JWT_SECRET: str = "video-scripts-secret-change-me"
    ADMIN_EMAIL: str = "admin@carbon.com"
    ADMIN_PASSWORD: str = "admin123"

    class Config:
        env_file = ".env"


settings = Settings()
