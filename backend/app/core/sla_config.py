"""
SLA Configuration by category as per Carbon requirements document.
Each category has response_hours (first response) and resolution_hours (full resolution).
"""

# SLA por categoria conforme documento de requisitos Carbon
SLA_BY_CATEGORY = {
    "chargeback": {"response_hours": 1, "resolution_hours": 24, "priority": "urgent"},
    "reclame_aqui": {"response_hours": 2, "resolution_hours": 48, "priority": "urgent"},
    "procon": {"response_hours": 2, "resolution_hours": 48, "priority": "urgent"},
    "defeito_garantia": {"response_hours": 4, "resolution_hours": 72, "priority": "high"},
    "troca": {"response_hours": 4, "resolution_hours": 72, "priority": "high"},
    "reenvio": {"response_hours": 4, "resolution_hours": 72, "priority": "high"},
    "mau_uso": {"response_hours": 8, "resolution_hours": 120, "priority": "medium"},
    "duvida": {"response_hours": 8, "resolution_hours": 48, "priority": "medium"},
    "rastreamento": {"response_hours": 4, "resolution_hours": 48, "priority": "medium"},
    "elogio": {"response_hours": 24, "resolution_hours": 168, "priority": "low"},
    "sugestao": {"response_hours": 24, "resolution_hours": 168, "priority": "low"},
    "outros": {"response_hours": 8, "resolution_hours": 72, "priority": "medium"},
}

# Default SLA by priority (fallback when category not matched)
SLA_BY_PRIORITY = {
    "urgent": {"response_hours": 1, "resolution_hours": 24},
    "high": {"response_hours": 4, "resolution_hours": 72},
    "medium": {"response_hours": 8, "resolution_hours": 120},
    "low": {"response_hours": 24, "resolution_hours": 168},
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

# Category routing — maps categories to specialties/inbox types
CATEGORY_ROUTING = {
    "chargeback": "juridico",
    "procon": "juridico",
    "reclame_aqui": "juridico",
    "defeito_garantia": "tecnico",
    "troca": "logistica",
    "reenvio": "logistica",
    "rastreamento": "logistica",
    "mau_uso": "tecnico",
}


def get_sla_for_ticket(category: str | None, priority: str) -> dict:
    """Returns {'response_hours': int, 'resolution_hours': int, 'priority': str}"""
    if category and category.lower() in SLA_BY_CATEGORY:
        config = SLA_BY_CATEGORY[category.lower()]
        return config
    fallback = SLA_BY_PRIORITY.get(priority, SLA_BY_PRIORITY["medium"])
    return {**fallback, "priority": priority}
