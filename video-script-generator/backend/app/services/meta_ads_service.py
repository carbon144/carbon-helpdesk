"""Integracao com Meta Ads API.

Puxa performance de anuncios para feedback loop:
- Vincula roteiros a ads
- Synca metricas de performance
- Identifica melhores e piores roteiros
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

META_GRAPH_URL = "https://graph.facebook.com/v21.0"


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.META_ADS_ACCESS_TOKEN}"}


async def get_ad_insights(ad_id: str, date_preset: str = "last_30d") -> dict | None:
    """Busca metricas de performance de um anuncio especifico."""
    if not settings.META_ADS_ACCESS_TOKEN:
        logger.warning("META_ADS_ACCESS_TOKEN nao configurado")
        return None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{META_GRAPH_URL}/{ad_id}/insights",
                headers=_headers(),
                params={
                    "fields": ",".join([
                        "impressions", "clicks", "ctr", "cpc", "cpm",
                        "spend", "conversions", "purchase_roas",
                        "video_p25_watched_actions", "video_p50_watched_actions",
                        "video_p75_watched_actions", "video_p100_watched_actions",
                        "video_play_actions",
                        "actions", "cost_per_action_type",
                    ]),
                    "date_preset": date_preset,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            if not data.get("data"):
                return None

            raw = data["data"][0]
            return _parse_insights(raw)
    except Exception as e:
        logger.error(f"Erro ao buscar insights do ad {ad_id}: {e}")
        return None


async def get_campaign_ads(campaign_id: str) -> list[dict]:
    """Lista todos os ads de uma campanha."""
    if not settings.META_ADS_ACCESS_TOKEN:
        return []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{META_GRAPH_URL}/{campaign_id}/ads",
                headers=_headers(),
                params={"fields": "id,name,status,creative{title,body}"},
            )
            resp.raise_for_status()
            return resp.json().get("data", [])
    except Exception as e:
        logger.error(f"Erro ao listar ads da campanha {campaign_id}: {e}")
        return []


async def get_account_campaigns() -> list[dict]:
    """Lista campanhas da conta de ads."""
    if not settings.META_ADS_ACCESS_TOKEN or not settings.META_ADS_ACCOUNT_ID:
        return []

    try:
        account_id = settings.META_ADS_ACCOUNT_ID
        if not account_id.startswith("act_"):
            account_id = f"act_{account_id}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{META_GRAPH_URL}/{account_id}/campaigns",
                headers=_headers(),
                params={
                    "fields": "id,name,status,objective,daily_budget,lifetime_budget",
                    "limit": 50,
                    "filtering": '[{"field":"status","operator":"IN","value":["ACTIVE","PAUSED"]}]',
                },
            )
            resp.raise_for_status()
            return resp.json().get("data", [])
    except Exception as e:
        logger.error(f"Erro ao listar campanhas: {e}")
        return []


async def sync_ad_performance(ad_id: str) -> dict | None:
    """Synca performance de um ad e retorna dados formatados para o model."""
    insights = await get_ad_insights(ad_id)
    if not insights:
        return None

    return {
        "impressions": insights.get("impressions"),
        "clicks": insights.get("clicks"),
        "ctr": insights.get("ctr"),
        "cpc": insights.get("cpc"),
        "cpm": insights.get("cpm"),
        "spend": insights.get("spend"),
        "conversions": insights.get("conversions"),
        "roas": insights.get("roas"),
        "video_views": insights.get("video_views"),
        "video_watch_25": insights.get("video_watch_25"),
        "video_watch_50": insights.get("video_watch_50"),
        "video_watch_75": insights.get("video_watch_75"),
        "video_watch_100": insights.get("video_watch_100"),
        "hook_rate": insights.get("hook_rate"),
        "hold_rate": insights.get("hold_rate"),
        "performance_synced_at": datetime.now(timezone.utc),
    }


def _parse_insights(raw: dict) -> dict:
    """Parseia resposta da Meta Ads API para formato limpo."""
    impressions = int(raw.get("impressions", 0))
    clicks = int(raw.get("clicks", 0))

    # Video watch percentages
    def _get_video_pct(actions_key: str) -> float | None:
        actions = raw.get(actions_key, [])
        if actions and isinstance(actions, list):
            return float(actions[0].get("value", 0))
        return None

    video_views_raw = raw.get("video_play_actions", [])
    video_views = int(video_views_raw[0]["value"]) if video_views_raw else None

    # Hook rate = 3s views / impressions (proxy)
    hook_rate = None
    if video_views and impressions > 0:
        hook_rate = round((video_views / impressions) * 100, 2)

    # Hold rate = 75% watched / total views
    v75 = _get_video_pct("video_p75_watched_actions")
    hold_rate = None
    if v75 and video_views and video_views > 0:
        hold_rate = round((v75 / video_views) * 100, 2)

    # ROAS
    roas_raw = raw.get("purchase_roas", [])
    roas = float(roas_raw[0]["value"]) if roas_raw else None

    # Conversions
    conversions = None
    for action in raw.get("actions", []):
        if action.get("action_type") in ("purchase", "offsite_conversion.fb_pixel_purchase"):
            conversions = int(action["value"])
            break

    return {
        "impressions": impressions,
        "clicks": clicks,
        "ctr": float(raw.get("ctr", 0)),
        "cpc": float(raw.get("cpc", 0)),
        "cpm": float(raw.get("cpm", 0)),
        "spend": float(raw.get("spend", 0)),
        "conversions": conversions,
        "roas": roas,
        "video_views": video_views,
        "video_watch_25": _get_video_pct("video_p25_watched_actions"),
        "video_watch_50": _get_video_pct("video_p50_watched_actions"),
        "video_watch_75": _get_video_pct("video_p75_watched_actions"),
        "video_watch_100": _get_video_pct("video_p100_watched_actions"),
        "hook_rate": hook_rate,
        "hold_rate": hold_rate,
    }
