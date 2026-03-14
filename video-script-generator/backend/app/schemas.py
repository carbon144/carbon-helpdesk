from __future__ import annotations
from pydantic import BaseModel
from datetime import datetime


# --- Script Types ---
SCRIPT_TYPES = {
    "teleprompter": "Teleprompter",
    "ugc": "UGC",
    "founder_ad": "Founder Ad",
    "meta_ad": "Meta Ad Completo",
}

TONE_OPTIONS = [
    "urgente", "conversacional", "autoritario", "emocional",
    "humoristico", "educativo", "aspiracional", "direto",
]


class ScriptBrief(BaseModel):
    """Brief para gerar um roteiro."""
    title: str
    product_name: str
    product_description: str | None = None
    objective: str | None = None
    target_audience: str | None = None
    tone: str | None = "conversacional"
    script_type: str = "teleprompter"
    duration_seconds: int | None = 30
    additional_notes: str | None = None
    use_customer_insights: bool = True
    tags: list[str] | None = None


class ScriptRefine(BaseModel):
    """Pedido de refinamento de um roteiro existente."""
    feedback: str
    keep_structure: bool = True


class ScriptLinkAd(BaseModel):
    """Vincular roteiro a um anuncio Meta."""
    meta_ad_id: str
    meta_campaign_id: str | None = None
    meta_adset_id: str | None = None


class ScriptRate(BaseModel):
    """Avaliar um roteiro."""
    rating: int  # 1-5
    notes: str | None = None


class ScriptUpdate(BaseModel):
    """Atualizar campos do roteiro."""
    title: str | None = None
    script_content: str | None = None
    is_favorite: bool | None = None
    tags: list[str] | None = None
    status: str | None = None


class ScriptOut(BaseModel):
    id: str
    title: str
    product_name: str
    product_description: str | None = None
    objective: str | None = None
    target_audience: str | None = None
    tone: str | None = None
    script_type: str
    duration_seconds: int | None = None
    additional_notes: str | None = None

    script_content: str | None = None
    scenes: dict | None = None
    hook_options: list | None = None
    cta_options: list | None = None
    thumbnail_suggestions: list | None = None
    customer_insights: dict | None = None

    meta_ad_id: str | None = None
    meta_campaign_id: str | None = None
    impressions: int | None = None
    clicks: int | None = None
    ctr: float | None = None
    cpc: float | None = None
    cpm: float | None = None
    spend: float | None = None
    conversions: int | None = None
    roas: float | None = None
    video_views: int | None = None
    hook_rate: float | None = None
    hold_rate: float | None = None
    performance_synced_at: datetime | None = None

    status: str
    rating: int | None = None
    rating_notes: str | None = None
    version: int
    parent_id: str | None = None
    is_favorite: bool
    tags: list[str] | None = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InsightOut(BaseModel):
    id: str
    insight_type: str
    content: str
    frequency: int
    product_name: str | None = None
    category: str | None = None
    last_seen_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class PerformanceStats(BaseModel):
    """Stats agregadas de performance dos roteiros."""
    total_scripts: int = 0
    scripts_with_ads: int = 0
    avg_ctr: float | None = None
    avg_roas: float | None = None
    avg_hook_rate: float | None = None
    best_script_id: str | None = None
    best_script_title: str | None = None
    best_roas: float | None = None
    total_spend: float | None = None
    total_conversions: int | None = None
    top_script_type: str | None = None
