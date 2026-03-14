"""API de roteiros de video."""
from __future__ import annotations
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.database import get_db
from app.models import VideoScript, CustomerInsight
from app.schemas import (
    ScriptBrief, ScriptRefine, ScriptLinkAd, ScriptRate,
    ScriptUpdate, ScriptOut, InsightOut, PerformanceStats,
    SCRIPT_TYPES, TONE_OPTIONS,
)
from app.services import script_generator, meta_ads_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scripts", tags=["scripts"])


# ─── Config / Options ────────────────────────────────────────────────

@router.get("/options")
async def get_options():
    """Retorna opcoes disponiveis para o formulario."""
    return {
        "script_types": SCRIPT_TYPES,
        "tone_options": TONE_OPTIONS,
        "duration_presets": [15, 30, 45, 60, 90],
    }


# ─── CRUD ─────────────────────────────────────────────────────────────

@router.get("/", response_model=list[ScriptOut])
async def list_scripts(
    status: str | None = None,
    script_type: str | None = None,
    is_favorite: bool | None = None,
    has_ad: bool | None = None,
    q: str | None = None,
    sort: str = "-created_at",
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Lista roteiros com filtros."""
    query = select(VideoScript)

    if status:
        query = query.where(VideoScript.status == status)
    if script_type:
        query = query.where(VideoScript.script_type == script_type)
    if is_favorite is not None:
        query = query.where(VideoScript.is_favorite == is_favorite)
    if has_ad is True:
        query = query.where(VideoScript.meta_ad_id.isnot(None))
    elif has_ad is False:
        query = query.where(VideoScript.meta_ad_id.is_(None))
    if q:
        search = f"%{q}%"
        query = query.where(
            VideoScript.title.ilike(search) |
            VideoScript.product_name.ilike(search) |
            VideoScript.script_content.ilike(search)
        )

    # Sorting
    if sort.startswith("-"):
        col = getattr(VideoScript, sort[1:], VideoScript.created_at)
        query = query.order_by(desc(col))
    else:
        col = getattr(VideoScript, sort, VideoScript.created_at)
        query = query.order_by(col)

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{script_id}", response_model=ScriptOut)
async def get_script(script_id: str, db: AsyncSession = Depends(get_db)):
    """Busca um roteiro por ID."""
    result = await db.execute(select(VideoScript).where(VideoScript.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(404, "Roteiro nao encontrado")
    return script


@router.patch("/{script_id}", response_model=ScriptOut)
async def update_script(
    script_id: str,
    data: ScriptUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Atualiza campos de um roteiro."""
    result = await db.execute(select(VideoScript).where(VideoScript.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(404, "Roteiro nao encontrado")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(script, field, value)

    await db.commit()
    await db.refresh(script)
    return script


@router.delete("/{script_id}")
async def delete_script(script_id: str, db: AsyncSession = Depends(get_db)):
    """Deleta um roteiro."""
    result = await db.execute(select(VideoScript).where(VideoScript.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(404, "Roteiro nao encontrado")
    await db.delete(script)
    await db.commit()
    return {"ok": True}


# ─── Generation ───────────────────────────────────────────────────────

@router.post("/generate", response_model=ScriptOut)
async def generate(brief: ScriptBrief, db: AsyncSession = Depends(get_db)):
    """Gera um novo roteiro a partir do brief."""
    # Buscar roteiros top pra referencia
    top_scripts = []
    top_result = await db.execute(
        select(VideoScript)
        .where(VideoScript.roas.isnot(None))
        .where(VideoScript.script_type == brief.script_type)
        .order_by(desc(VideoScript.roas))
        .limit(3)
    )
    for s in top_result.scalars().all():
        top_scripts.append({
            "script_content": s.script_content,
            "roas": s.roas,
            "ctr": s.ctr,
        })

    # Criar registro no banco
    script = VideoScript(
        title=brief.title,
        product_name=brief.product_name,
        product_description=brief.product_description,
        objective=brief.objective,
        target_audience=brief.target_audience,
        tone=brief.tone,
        script_type=brief.script_type,
        duration_seconds=brief.duration_seconds,
        additional_notes=brief.additional_notes,
        tags=brief.tags,
        status="generating",
    )
    db.add(script)
    await db.commit()
    await db.refresh(script)

    try:
        result = await script_generator.generate_script(
            title=brief.title,
            product_name=brief.product_name,
            script_type=brief.script_type,
            product_description=brief.product_description,
            objective=brief.objective,
            target_audience=brief.target_audience,
            tone=brief.tone,
            duration_seconds=brief.duration_seconds,
            additional_notes=brief.additional_notes,
            use_customer_insights=brief.use_customer_insights,
            top_performing_scripts=top_scripts if top_scripts else None,
        )

        script.script_content = result.get("script", "")
        script.scenes = result.get("scenes")
        script.hook_options = result.get("hook_options")
        script.cta_options = result.get("cta_options")
        script.thumbnail_suggestions = result.get("thumbnail_suggestions")
        script.customer_insights = result.get("customer_insights")
        script.metadata = {
            k: v for k, v in result.items()
            if k not in ("script", "scenes", "hook_options", "cta_options", "thumbnail_suggestions", "customer_insights")
        }
        script.status = "completed"

    except Exception as e:
        logger.error(f"Erro ao gerar roteiro: {e}")
        script.status = "error"
        script.error_message = str(e)[:500]

    await db.commit()
    await db.refresh(script)
    return script


@router.post("/{script_id}/refine", response_model=ScriptOut)
async def refine(
    script_id: str,
    data: ScriptRefine,
    db: AsyncSession = Depends(get_db),
):
    """Refina um roteiro existente, criando nova versao."""
    result = await db.execute(select(VideoScript).where(VideoScript.id == script_id))
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(404, "Roteiro nao encontrado")

    try:
        refined = await script_generator.refine_script(
            original_script=original.script_content or "",
            script_type=original.script_type,
            feedback=data.feedback,
            keep_structure=data.keep_structure,
        )

        new_script = VideoScript(
            title=f"{original.title} (v{original.version + 1})",
            product_name=original.product_name,
            product_description=original.product_description,
            objective=original.objective,
            target_audience=original.target_audience,
            tone=original.tone,
            script_type=original.script_type,
            duration_seconds=original.duration_seconds,
            additional_notes=original.additional_notes,
            tags=original.tags,
            script_content=refined.get("script", ""),
            scenes=refined.get("scenes"),
            hook_options=refined.get("hook_options"),
            cta_options=refined.get("cta_options"),
            thumbnail_suggestions=refined.get("thumbnail_suggestions"),
            customer_insights=original.customer_insights,
            version=original.version + 1,
            parent_id=original.id,
            status="completed",
        )
        db.add(new_script)
        await db.commit()
        await db.refresh(new_script)
        return new_script

    except Exception as e:
        logger.error(f"Erro ao refinar roteiro: {e}")
        raise HTTPException(500, f"Erro ao refinar: {str(e)[:200]}")


# ─── Meta Ads Integration ────────────────────────────────────────────

@router.post("/{script_id}/link-ad", response_model=ScriptOut)
async def link_ad(
    script_id: str,
    data: ScriptLinkAd,
    db: AsyncSession = Depends(get_db),
):
    """Vincula um roteiro a um anuncio Meta Ads."""
    result = await db.execute(select(VideoScript).where(VideoScript.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(404, "Roteiro nao encontrado")

    script.meta_ad_id = data.meta_ad_id
    script.meta_campaign_id = data.meta_campaign_id
    script.meta_adset_id = data.meta_adset_id

    await db.commit()
    await db.refresh(script)
    return script


@router.post("/{script_id}/sync-performance", response_model=ScriptOut)
async def sync_performance(script_id: str, db: AsyncSession = Depends(get_db)):
    """Synca metricas de performance do Meta Ads para o roteiro."""
    result = await db.execute(select(VideoScript).where(VideoScript.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(404, "Roteiro nao encontrado")
    if not script.meta_ad_id:
        raise HTTPException(400, "Roteiro nao vinculado a um anuncio")

    perf = await meta_ads_service.sync_ad_performance(script.meta_ad_id)
    if not perf:
        raise HTTPException(502, "Nao foi possivel buscar metricas do Meta Ads")

    for field, value in perf.items():
        setattr(script, field, value)

    await db.commit()
    await db.refresh(script)
    return script


@router.post("/sync-all-performance")
async def sync_all_performance(db: AsyncSession = Depends(get_db)):
    """Synca performance de todos os roteiros vinculados a ads."""
    result = await db.execute(
        select(VideoScript).where(VideoScript.meta_ad_id.isnot(None))
    )
    scripts = result.scalars().all()
    synced = 0
    errors = 0

    for script in scripts:
        try:
            perf = await meta_ads_service.sync_ad_performance(script.meta_ad_id)
            if perf:
                for field, value in perf.items():
                    setattr(script, field, value)
                synced += 1
        except Exception as e:
            logger.warning(f"Erro ao syncar performance do script {script.id}: {e}")
            errors += 1

    await db.commit()
    return {"synced": synced, "errors": errors, "total": len(scripts)}


@router.get("/meta/campaigns")
async def list_campaigns():
    """Lista campanhas da conta Meta Ads."""
    campaigns = await meta_ads_service.get_account_campaigns()
    return {"campaigns": campaigns}


@router.get("/meta/campaigns/{campaign_id}/ads")
async def list_campaign_ads(campaign_id: str):
    """Lista ads de uma campanha."""
    ads = await meta_ads_service.get_campaign_ads(campaign_id)
    return {"ads": ads}


# ─── Rating ───────────────────────────────────────────────────────────

@router.post("/{script_id}/rate", response_model=ScriptOut)
async def rate_script(
    script_id: str,
    data: ScriptRate,
    db: AsyncSession = Depends(get_db),
):
    """Avalia um roteiro (1-5)."""
    if not 1 <= data.rating <= 5:
        raise HTTPException(400, "Rating deve ser entre 1 e 5")

    result = await db.execute(select(VideoScript).where(VideoScript.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(404, "Roteiro nao encontrado")

    script.rating = data.rating
    script.rating_notes = data.notes
    await db.commit()
    await db.refresh(script)
    return script


# ─── Insights ─────────────────────────────────────────────────────────

@router.get("/insights/customer")
async def get_customer_insights(product_name: str | None = None):
    """Busca insights dos clientes do helpdesk."""
    from app.services.helpdesk_client import extract_customer_insights
    insights = await extract_customer_insights(product_name)

    summary = None
    if insights.get("total_tickets_analyzed", 0) > 0:
        try:
            summary = await script_generator.generate_insights_summary(insights)
        except Exception as e:
            logger.warning(f"Erro ao gerar resumo de insights: {e}")

    return {"insights": insights, "summary": summary}


# ─── Performance Dashboard ───────────────────────────────────────────

@router.get("/stats/performance", response_model=PerformanceStats)
async def get_performance_stats(db: AsyncSession = Depends(get_db)):
    """Retorna stats agregadas de performance."""
    total_result = await db.execute(select(func.count(VideoScript.id)))
    total = total_result.scalar() or 0

    ads_result = await db.execute(
        select(func.count(VideoScript.id)).where(VideoScript.meta_ad_id.isnot(None))
    )
    with_ads = ads_result.scalar() or 0

    # Medias
    avg_result = await db.execute(
        select(
            func.avg(VideoScript.ctr),
            func.avg(VideoScript.roas),
            func.avg(VideoScript.hook_rate),
            func.sum(VideoScript.spend),
            func.sum(VideoScript.conversions),
        ).where(VideoScript.meta_ad_id.isnot(None))
    )
    row = avg_result.one_or_none()

    # Melhor roteiro
    best_result = await db.execute(
        select(VideoScript)
        .where(VideoScript.roas.isnot(None))
        .order_by(desc(VideoScript.roas))
        .limit(1)
    )
    best = best_result.scalar_one_or_none()

    # Tipo mais usado com ads
    type_result = await db.execute(
        select(VideoScript.script_type, func.count(VideoScript.id).label("cnt"))
        .where(VideoScript.meta_ad_id.isnot(None))
        .group_by(VideoScript.script_type)
        .order_by(desc("cnt"))
        .limit(1)
    )
    top_type_row = type_result.one_or_none()

    return PerformanceStats(
        total_scripts=total,
        scripts_with_ads=with_ads,
        avg_ctr=round(row[0], 2) if row and row[0] else None,
        avg_roas=round(row[1], 2) if row and row[1] else None,
        avg_hook_rate=round(row[2], 2) if row and row[2] else None,
        total_spend=round(row[3], 2) if row and row[3] else None,
        total_conversions=int(row[4]) if row and row[4] else None,
        best_script_id=best.id if best else None,
        best_script_title=best.title if best else None,
        best_roas=best.roas if best else None,
        top_script_type=top_type_row[0] if top_type_row else None,
    )
