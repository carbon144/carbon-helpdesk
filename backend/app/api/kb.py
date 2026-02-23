from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.kb_article import KBArticle
from app.models.macro import Macro
from app.schemas.kb import (
    KBArticleCreate, KBArticleUpdate, KBArticleResponse,
    MacroCreate, MacroUpdate, MacroResponse,
)

router = APIRouter(prefix="/kb", tags=["knowledge-base"])


# ── Articles ──

@router.get("/articles", response_model=list[KBArticleResponse])
async def list_articles(
    category: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(KBArticle).where(KBArticle.is_published == True)
    if category:
        query = query.where(KBArticle.category == category)
    if search:
        query = query.where(KBArticle.title.ilike(f"%{search}%"))
    query = query.order_by(KBArticle.updated_at.desc())

    result = await db.execute(query)
    return [KBArticleResponse.model_validate(a) for a in result.scalars().all()]


@router.get("/articles/{article_id}", response_model=KBArticleResponse)
async def get_article(article_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(KBArticle).where(KBArticle.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Artigo não encontrado")
    return KBArticleResponse.model_validate(article)


@router.post("/articles", response_model=KBArticleResponse, status_code=201)
async def create_article(body: KBArticleCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    article = KBArticle(
        title=body.title,
        content=body.content,
        category=body.category,
        tags=body.tags,
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)
    return KBArticleResponse.model_validate(article)


@router.patch("/articles/{article_id}", response_model=KBArticleResponse)
async def update_article(article_id: str, body: KBArticleUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(KBArticle).where(KBArticle.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Artigo não encontrado")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(article, field, value)
    await db.commit()
    await db.refresh(article)
    return KBArticleResponse.model_validate(article)


@router.post("/articles/reseed")
async def reseed_articles(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Delete all KB articles and insert real ones from Crisp/website."""
    if user.role not in ("admin", "supervisor"):
        raise HTTPException(status_code=403, detail="Apenas admins podem executar reseed")
    from app.services.seed_kb import reseed_kb
    count = await reseed_kb(db)
    return {"ok": True, "articles_inserted": count}


@router.delete("/articles/{article_id}")
async def delete_article(article_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(KBArticle).where(KBArticle.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Artigo não encontrado")
    await db.delete(article)
    await db.commit()
    return {"ok": True}


# ── Macros ──

@router.get("/macros", response_model=list[MacroResponse])
async def list_macros(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Macro).where(Macro.is_active == True).order_by(Macro.name))
    return [MacroResponse.model_validate(m) for m in result.scalars().all()]


@router.post("/macros", response_model=MacroResponse, status_code=201)
async def create_macro(body: MacroCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    actions_raw = [a.model_dump() for a in body.actions] if body.actions else None
    macro = Macro(name=body.name, content=body.content, category=body.category, actions=actions_raw)
    db.add(macro)
    await db.commit()
    await db.refresh(macro)
    return MacroResponse.model_validate(macro)


@router.patch("/macros/{macro_id}", response_model=MacroResponse)
async def update_macro(macro_id: str, body: MacroUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Macro).where(Macro.id == macro_id))
    macro = result.scalar_one_or_none()
    if not macro:
        raise HTTPException(status_code=404, detail="Macro não encontrada")

    data = body.model_dump(exclude_unset=True)
    if "actions" in data and data["actions"] is not None:
        data["actions"] = [a.model_dump() if hasattr(a, "model_dump") else a for a in body.actions]

    for field, value in data.items():
        setattr(macro, field, value)
    await db.commit()
    await db.refresh(macro)
    return MacroResponse.model_validate(macro)


@router.delete("/macros/{macro_id}")
async def delete_macro(macro_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Macro).where(Macro.id == macro_id))
    macro = result.scalar_one_or_none()
    if not macro:
        raise HTTPException(status_code=404, detail="Macro não encontrada")
    await db.delete(macro)
    await db.commit()
    return {"ok": True}
