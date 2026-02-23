"""Replace demo KB articles with real ones from Crisp Help Center and website."""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models.kb_article import KBArticle
from app.services.kb_real_data import KB_ARTICLES

logger = logging.getLogger(__name__)


async def reseed_kb(db: AsyncSession):
    """Delete all existing KB articles and insert real ones."""
    # Delete all existing articles
    await db.execute(delete(KBArticle))
    await db.flush()
    logger.info("Deleted all existing KB articles")

    # Insert real articles
    for art in KB_ARTICLES:
        article = KBArticle(
            title=art["title"],
            content=art["content"],
            category=art["category"],
            tags=art["tags"],
            is_published=True,
        )
        db.add(article)

    await db.commit()
    logger.info(f"Inserted {len(KB_ARTICLES)} real KB articles")
    return len(KB_ARTICLES)
