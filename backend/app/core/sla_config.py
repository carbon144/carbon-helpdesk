"""
SLA Configuration for Carbon Helpdesk.
SLA follows PRIORITY, not category.
Category = O QUÊ (routing). Priority = QUANDO (SLA).
"""
from __future__ import annotations

# SLA por prioridade — fonte única de verdade
SLA_BY_PRIORITY = {
    "urgent": {"response_hours": 1, "resolution_hours": 24},
    "high":   {"response_hours": 4, "resolution_hours": 72},
    "medium": {"response_hours": 8, "resolution_hours": 72},
    "low":    {"response_hours": 24, "resolution_hours": 168},
}

# Blacklist auto-rules
BLACKLIST_RULES = {
    "max_chargebacks": 3,       # 3+ chargebacks = blacklist
    "max_resends": 2,           # 2+ reenvios em 6 meses = flag
    "max_abuse_flags": 3,       # 3+ flags de abuso = blacklist
}

# Auto-escalation rules (in hours without agent response)
ESCALATION_RULES = {
    "urgent": {"warn_hours": 1, "escalate_hours": 2},
    "high": {"warn_hours": 2, "escalate_hours": 4},
    "medium": {"warn_hours": 4, "escalate_hours": 8},
    "low": {"warn_hours": 8, "escalate_hours": 24},
}

# Category routing — maps categories to agent specialties.
# Today all agents are generalists (specialty=geral/null), so this falls through
# to round-robin. When specialized agents are hired, fill user.specialty in DB.
CATEGORY_ROUTING = {
    "garantia":   "tecnico",
    "reenvio":    "logistica",
    "meu_pedido": "logistica",
    "financeiro": "financeiro",
}
# reclamacao and duvida → round-robin (any agent)


def get_sla_for_ticket(category: str | None, priority: str) -> dict:
    """Returns {'response_hours': int, 'resolution_hours': int, 'priority': str}.
    SLA is driven by priority only. Category param kept for backward compat."""
    sla = SLA_BY_PRIORITY.get(priority, SLA_BY_PRIORITY["medium"])
    return {**sla, "priority": priority}
