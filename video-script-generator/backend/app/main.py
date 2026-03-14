import logging
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.api import scripts

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando Video Script Generator...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database pronta.")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Carbon Video Script Generator",
    description="Gerador automatico de roteiros de video para Meta Ads",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scripts.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "video-script-generator",
        "helpdesk_url": settings.HELPDESK_API_URL,
        "meta_ads_configured": bool(settings.META_ADS_ACCESS_TOKEN),
        "ai_configured": bool(settings.ANTHROPIC_API_KEY),
    }
