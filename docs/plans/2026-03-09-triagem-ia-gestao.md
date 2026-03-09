# Triagem Inteligente + Gestao IA — Plano de Implementacao

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transformar o helpdesk num sistema inteligente com IA respondendo 40-50% dos tickets, triagem configuravel pelo Victor, dashboard de gestao com KPIs, monitoramento do Reclame Aqui, e deteccao automatica de agentes online.

**Architecture:** Backend FastAPI existente + novos services (ai_email_responder, triage_rules, ra_monitor) + novos models (TriageRule, AgentActivity) + frontend React pages (TriagemPage, LeaderDashboard). IA usa Claude Haiku pra triagem e Sonnet pra respostas. Gmail service existente pra envio.

**Tech Stack:** FastAPI, SQLAlchemy async, PostgreSQL, React, Claude API (Anthropic), Gmail API, Playwright (RA scraping)

**Contexto de negocio critico (IA precisa saber):**
- GUACU NEGOCIOS DIGITAIS LTDA (CNPJ 48.769.355/0001-76) = Carbon Relogios Inteligentes (mesma empresa)
- Garantia: 12 meses (aumentou de 90 dias recentemente)
- Nao tem assistencia tecnica — troca direta na garantia ou cupom apos garantia
- Problema de importacao jan-fev 2026: cadastro errado no AliExpress fez pedidos serem barrados na alfandega. Alguns reenviados foram barrados 2x. JA CORRIGIDO — pedidos novos estao normais.
- Estorno: prazo normal de fatura (1-2 faturas), nao 3 meses
- Equipe: Victor (lider), Daniele/Luana/Reinan (atendentes), Tauane (trocas, separada)

**REGRA DE OURO DA IA — NAO INVENTAR:**
A IA NUNCA pode inventar informacao. Se nao sabe, encaminha pro humano. Especificamente:
- NAO prometer brinde, desconto ou cupom
- NAO prometer prioridade no envio
- NAO prometer cancelamento ou estorno
- NAO inventar prazos especificos de entrega
- NAO inventar status de pedido ou rastreio
- NAO prometer que vai resolver X em Y dias
- NAO dar informacao que nao foi explicitamente confirmada
- Se nao tem certeza de NADA → "Encaminhei pro time, vao te responder em ate 24h uteis"
A IA so pode afirmar FATOS CONCRETOS: GUACU = Carbon, garantia 12 meses, sem assistencia tecnica, troca direta.

---

## Task 1: Limpar categorias duplicadas no banco

**Files:**
- Modify: `backend/app/services/ai_service.py:150-198` (TRIAGE_SYSTEM_PROMPT)
- Modify: `backend/app/core/sla_config.py:51-61` (CATEGORY_ROUTING)
- Run: migration SQL direto no banco

**Step 1: Atualizar TRIAGE_SYSTEM_PROMPT com categorias limpas**

Em `backend/app/services/ai_service.py`, substituir o bloco CATEGORIAS do prompt por:

```
CATEGORIAS (use exatamente estes valores):
- atraso_entrega: produto nao chegou, rastreio parado, demora na entrega, importacao
- defeito_produto: produto com defeito, tela, bluetooth, carregador, GPS, garantia
- reenvio: produto extraviado, precisa reenviar, nao recebeu e quer novo envio
- duvida_geral: duvida sobre produto, funcionalidades, compra, elogio, feedback positivo
- propaganda_enganosa: cliente acha que eh golpe, menciona GUACU, propaganda falsa
- suporte_tecnico: problemas de software, app, bluetooth, configuracao, mau uso
- financeiro: reembolso, estorno, pagamento, nota fiscal, cancelamento
- troca_devolucao: troca de tamanho, cor, modelo, devolucao, arrependimento
- juridico_risco: PROCON, processo, advogado, danos morais, juizado, chargeback, Reclame Aqui
- reclamacao: reclamacao generica, mau atendimento, insatisfacao geral
```

**Step 2: Atualizar CATEGORY_ROUTING**

Em `backend/app/core/sla_config.py`:

```python
CATEGORY_ROUTING = {
    "juridico_risco": "juridico",
    "defeito_produto": "tecnico",
    "suporte_tecnico": "tecnico",
    "troca_devolucao": "logistica",
    "reenvio": "logistica",
    "atraso_entrega": "logistica",
}
```

**Step 3: Migrar categorias existentes no banco**

```sql
UPDATE tickets SET category = 'atraso_entrega' WHERE category IN ('rastreamento', 'entrega_rastreio');
UPDATE tickets SET category = 'defeito_produto' WHERE category IN ('defeito_garantia', 'garantia', 'carregador', 'garantia_devolucoes');
UPDATE tickets SET category = 'juridico_risco' WHERE category IN ('procon', 'chargeback', 'reclame_aqui', 'juridico');
UPDATE tickets SET category = 'troca_devolucao' WHERE category = 'troca';
UPDATE tickets SET category = 'duvida_geral' WHERE category IN ('duvida', 'elogio', 'outros');
UPDATE tickets SET category = 'financeiro' WHERE category = 'cancelamento';
-- ai_category tambem
UPDATE tickets SET ai_category = 'atraso_entrega' WHERE ai_category IN ('rastreamento', 'entrega_rastreio');
UPDATE tickets SET ai_category = 'defeito_produto' WHERE ai_category IN ('defeito_garantia', 'garantia', 'carregador', 'garantia_devolucoes');
UPDATE tickets SET ai_category = 'juridico_risco' WHERE ai_category IN ('procon', 'chargeback', 'reclame_aqui', 'juridico');
UPDATE tickets SET ai_category = 'troca_devolucao' WHERE ai_category = 'troca';
UPDATE tickets SET ai_category = 'duvida_geral' WHERE ai_category IN ('duvida', 'elogio', 'outros');
UPDATE tickets SET ai_category = 'financeiro' WHERE ai_category = 'cancelamento';
```

**Step 4: Commit**

```bash
git add backend/app/services/ai_service.py backend/app/core/sla_config.py
git commit -m "refactor: consolidar categorias de tickets (20 -> 10)"
```

---

## Task 2: Model TriageRule + AgentActivity

**Files:**
- Create: `backend/app/models/triage_rule.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/models/user.py` (add last_activity_at)

**Step 1: Criar model TriageRule**

```python
# backend/app/models/triage_rule.py
import uuid
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB

from app.core.database import Base


class TriageRule(Base):
    __tablename__ = "triage_rules"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)  # higher = checked first

    # Conditions (all optional, AND logic — all non-null must match)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    priority_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # low/medium/high/urgent
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # gmail/whatsapp/instagram
    keywords: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)  # any keyword in subject/body
    sentiment: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Actions
    assign_to: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    assign_to_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # round-robin within role
    set_priority: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    set_tags: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    auto_reply: Mapped[bool] = mapped_column(Boolean, default=False)  # let AI auto-respond

    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    agent = relationship("User", foreign_keys=[assign_to], lazy="selectin")
```

**Step 2: Adicionar last_activity_at no User model**

Em `backend/app/models/user.py`, adicionar apos `last_login`:

```python
last_activity_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
```

**Step 3: Importar no __init__.py e gerar migration**

```bash
# No servidor:
docker exec carbon-backend alembic revision --autogenerate -m "add triage_rules and user last_activity_at"
docker exec carbon-backend alembic upgrade head
```

**Step 4: Commit**

```bash
git add backend/app/models/triage_rule.py backend/app/models/user.py backend/app/models/__init__.py
git commit -m "feat: add TriageRule model and User.last_activity_at"
```

---

## Task 3: API de Triagem (CRUD regras + engine)

**Files:**
- Create: `backend/app/api/triage.py`
- Create: `backend/app/services/triage_service.py`
- Modify: `backend/app/api/__init__.py` (registrar router)

**Step 1: Criar triage_service.py**

```python
# backend/app/services/triage_service.py
"""Triage engine: applies Victor's rules + fallback round-robin."""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.triage_rule import TriageRule
from app.models.ticket import Ticket
from app.models.user import User

logger = logging.getLogger(__name__)

ONLINE_THRESHOLD_MINUTES = 15


async def get_online_agents(db: AsyncSession) -> list[User]:
    """Return agents who are online (activity < 15min)."""
    threshold = datetime.now(timezone.utc) - timedelta(minutes=ONLINE_THRESHOLD_MINUTES)
    result = await db.execute(
        select(User).where(
            User.is_active == True,
            User.role.in_(["agent", "supervisor", "admin"]),
            User.last_activity_at >= threshold,
        )
    )
    return list(result.scalars().all())


async def apply_triage_rules(ticket: Ticket, db: AsyncSession) -> dict:
    """Apply triage rules to a ticket. Returns action taken."""
    rules = await db.execute(
        select(TriageRule)
        .where(TriageRule.is_active == True)
        .order_by(TriageRule.priority.desc())
    )
    rules = list(rules.scalars().all())

    for rule in rules:
        if _rule_matches(rule, ticket):
            return await _apply_rule(rule, ticket, db)

    # Fallback: round-robin among online agents
    return await _fallback_round_robin(ticket, db)


def _rule_matches(rule: TriageRule, ticket: Ticket) -> bool:
    """Check if all non-null conditions match."""
    if rule.category and ticket.category != rule.category:
        return False
    if rule.priority_level and ticket.priority != rule.priority_level:
        return False
    if rule.source and ticket.source != rule.source:
        return False
    if rule.sentiment and ticket.sentiment != rule.sentiment:
        return False
    if rule.keywords:
        text = f"{ticket.subject or ''} ".lower()
        if not any(kw.lower() in text for kw in rule.keywords):
            return False
    return True


async def _apply_rule(rule: TriageRule, ticket: Ticket, db: AsyncSession) -> dict:
    """Apply a matched rule's actions."""
    result = {"rule_id": rule.id, "rule_name": rule.name, "actions": []}

    if rule.set_priority:
        ticket.priority = rule.set_priority
        result["actions"].append(f"priority={rule.set_priority}")

    if rule.set_tags:
        existing = list(ticket.tags or [])
        ticket.tags = list(set(existing + rule.set_tags))
        result["actions"].append(f"tags+={rule.set_tags}")

    if rule.assign_to:
        ticket.assigned_to = rule.assign_to
        result["actions"].append(f"assigned_to={rule.assign_to}")
    elif rule.assign_to_role:
        # Round-robin among online agents with this role/specialty
        agent = await _pick_online_agent(db, specialty=rule.assign_to_role)
        if agent:
            ticket.assigned_to = agent.id
            result["actions"].append(f"assigned_to={agent.name} (role:{rule.assign_to_role})")

    result["auto_reply"] = rule.auto_reply
    return result


async def _fallback_round_robin(ticket: Ticket, db: AsyncSession) -> dict:
    """Fallback: assign to online agent with least tickets."""
    agent = await _pick_online_agent(db)
    if agent:
        ticket.assigned_to = agent.id
        return {"rule_id": None, "rule_name": "round-robin", "actions": [f"assigned_to={agent.name}"], "auto_reply": False}
    # Nobody online — mark for AI auto-reply
    return {"rule_id": None, "rule_name": "no-agents-online", "actions": ["queued"], "auto_reply": True}


async def _pick_online_agent(db: AsyncSession, specialty: str = None) -> User | None:
    """Pick online agent with fewest open tickets."""
    online = await get_online_agents(db)
    if not online:
        return None

    if specialty:
        specialists = [a for a in online if getattr(a, 'specialty', None) == specialty]
        if specialists:
            online = specialists

    # Get ticket counts
    agent_loads = {}
    for agent in online:
        count_result = await db.execute(
            select(func.count()).select_from(Ticket).where(
                Ticket.assigned_to == agent.id,
                Ticket.status.in_(["open", "in_progress", "waiting", "analyzing", "waiting_supplier", "waiting_resend"])
            )
        )
        load = count_result.scalar()
        if load < agent.max_tickets:
            agent_loads[agent.id] = (load, agent)

    if not agent_loads:
        return None

    # Pick agent with least load
    _, chosen = min(agent_loads.values(), key=lambda x: x[0])
    return chosen
```

**Step 2: Criar API triage.py (CRUD + trigger)**

```python
# backend/app/api/triage.py
"""Triage rules API — Victor configures, system executes."""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.triage_rule import TriageRule
from app.services.triage_service import get_online_agents

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/triage", tags=["triage"])


@router.get("/rules")
async def list_rules(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(TriageRule).order_by(TriageRule.priority.desc()))
    rules = result.scalars().all()
    return [_rule_to_dict(r) for r in rules]


@router.post("/rules")
async def create_rule(request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in ("admin", "super_admin", "supervisor"):
        raise HTTPException(403, "Apenas lider/admin pode criar regras")
    data = await request.json()
    rule = TriageRule(created_by=user.id, **{k: v for k, v in data.items() if k != "id" and hasattr(TriageRule, k)})
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return _rule_to_dict(rule)


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in ("admin", "super_admin", "supervisor"):
        raise HTTPException(403, "Apenas lider/admin pode editar regras")
    result = await db.execute(select(TriageRule).where(TriageRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Regra nao encontrada")
    data = await request.json()
    for k, v in data.items():
        if hasattr(rule, k) and k not in ("id", "created_by", "created_at"):
            setattr(rule, k, v)
    await db.commit()
    return _rule_to_dict(rule)


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in ("admin", "super_admin", "supervisor"):
        raise HTTPException(403, "Apenas lider/admin pode deletar regras")
    result = await db.execute(select(TriageRule).where(TriageRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404)
    await db.delete(rule)
    await db.commit()
    return {"ok": True}


@router.get("/online-agents")
async def list_online_agents(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    agents = await get_online_agents(db)
    return [{"id": a.id, "name": a.name, "role": a.role, "specialty": a.specialty, "status": "online"} for a in agents]


def _rule_to_dict(r: TriageRule) -> dict:
    return {
        "id": r.id, "name": r.name, "is_active": r.is_active, "priority": r.priority,
        "category": r.category, "priority_level": r.priority_level, "source": r.source,
        "keywords": r.keywords, "sentiment": r.sentiment, "assign_to": r.assign_to,
        "assign_to_role": r.assign_to_role, "set_priority": r.set_priority,
        "set_tags": r.set_tags, "auto_reply": r.auto_reply,
        "agent_name": r.agent.name if r.agent else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
```

**Step 3: Registrar router e commit**

Adicionar em `backend/app/api/__init__.py` ou `main.py` onde os routers sao registrados:
```python
from app.api.triage import router as triage_router
app.include_router(triage_router, prefix="/api")
```

```bash
git add backend/app/api/triage.py backend/app/services/triage_service.py
git commit -m "feat: triage rules API + engine with online detection"
```

---

## Task 4: Middleware de atividade do agente

**Files:**
- Modify: `backend/app/core/security.py` ou middleware

**Step 1: Atualizar last_activity_at em cada request autenticado**

Adicionar no `get_current_user` dependency (em `backend/app/core/security.py`), apos validar o token:

```python
# No final de get_current_user, antes do return:
from datetime import datetime, timezone
if user.last_activity_at is None or (datetime.now(timezone.utc) - user.last_activity_at).total_seconds() > 60:
    user.last_activity_at = datetime.now(timezone.utc)
    db.add(user)
    await db.commit()
```

Nota: so atualiza se passou >60s pra nao sobrecarregar o DB.

**Step 2: Commit**

```bash
git add backend/app/core/security.py
git commit -m "feat: track agent last_activity_at on each request"
```

---

## Task 5: IA Auto-Reply Email

**Files:**
- Create: `backend/app/services/ai_email_responder.py`
- Modify: `backend/app/api/gmail.py:337-364` (hook no fetch_emails)

**Step 1: Criar ai_email_responder.py**

```python
# backend/app/services/ai_email_responder.py
"""AI auto-responder for email tickets."""
import logging
from app.services.ai_service import get_client, _call_with_retry, is_credits_exhausted, _handle_credit_error
from app.core.config import settings

logger = logging.getLogger(__name__)

# Categories the AI can auto-resolve
AUTO_RESOLVE_CATEGORIES = ["atraso_entrega", "duvida_geral", "propaganda_enganosa"]
# Categories AI can partially help (draft response, but needs human review)
AI_ASSIST_CATEGORIES = ["reenvio", "suporte_tecnico", "financeiro", "reclamacao"]

CARBON_CONTEXT = """Voce eh o atendimento da Carbon Relogios Inteligentes (nome fantasia).
Razao social: GUACU NEGOCIOS DIGITAIS LTDA, CNPJ 48.769.355/0001-76. Eh a MESMA empresa.

FATOS QUE VOCE SABE E PODE AFIRMAR:
- GUACU NEGOCIOS DIGITAIS = Carbon Relogios Inteligentes. Mesma empresa, mesmo CNPJ. Nao eh golpe.
- Garantia: 12 meses contra defeitos de fabricacao.
- Nao temos assistencia tecnica. Fazemos troca direta dentro da garantia.
- Apos a garantia: oferecemos cupom de desconto pra nova compra.
- Estorno: segue prazo normal da operadora do cartao, cai na proxima fatura ou na seguinte.
- Houve atrasos em pedidos de jan-fev 2026 por um problema de cadastro na importacao. Ja foi corrigido. Pedidos novos estao normais.
- Canais de atendimento: email suporte@carbonsmartwatch.com.br e WhatsApp.
- Para trocas/defeitos dentro da garantia: entrar em contato pelo email com numero do pedido.

COISAS QUE VOCE NAO SABE E NAO PODE FALAR:
- Status especifico de nenhum pedido (voce nao tem acesso)
- Codigo de rastreio (voce nao tem acesso)
- Prazo exato de entrega de nenhum pedido
- Se vai ter reembolso, cancelamento ou troca (quem decide eh o time)
- Qualquer brinde, desconto ou promocao
- Qualquer priorizacao de envio

Tom: casual, empatico, direto. Sem introducoes longas. Va direto ao ponto.
Assine como "Equipe Carbon"."""

AUTO_REPLY_PROMPT = f"""Voce eh o atendente IA da Carbon Smartwatch.

{CARBON_CONTEXT}

SUA UNICA FUNCAO: responder o que voce SABE e encaminhar o que voce NAO SABE.

FLUXO DE DECISAO:
1. Cliente acha que eh golpe/GUACU → Explique que eh a mesma empresa. RESOLVIDO.
2. Duvida sobre garantia/politica → Responda com os fatos acima. RESOLVIDO.
3. Pedido atrasado de jan-fev → Explique o problema de importacao, diga que ja foi corrigido, e que o time vai verificar o status especifico do pedido dele. ENCAMINHA.
4. Quer rastreio/status de pedido → Diga que recebeu a mensagem e o time vai verificar e responder com o status. ENCAMINHA.
5. Quer cancelamento/estorno/troca → Diga que registrou o pedido e o time vai analisar. ENCAMINHA.
6. Defeito/problema tecnico → Diga que registrou e o time de suporte vai orientar sobre a troca. ENCAMINHA.
7. Qualquer outra coisa que voce nao tem certeza → ENCAMINHA.

Quando ENCAMINHAR: diga "Ja encaminhei pro time responsavel e voce vai receber uma resposta em ate 24 horas uteis."

PROIBIDO: inventar qualquer informacao. Se nao esta na lista de FATOS acima, voce NAO sabe.
Maximo 3 paragrafos. Sem markdown. Texto puro.

Retorne APENAS o texto da resposta."""


async def should_auto_reply(category: str, priority: str, legal_risk: bool) -> bool:
    """Check if this ticket should get an AI auto-reply."""
    if legal_risk:
        return False
    if priority in ("urgent", "high"):
        return False
    if category in AUTO_RESOLVE_CATEGORIES:
        return True
    return False


async def generate_auto_reply(subject: str, body: str, customer_name: str, category: str, shopify_data: dict = None) -> str | None:
    """Generate an AI auto-reply for the ticket."""
    if is_credits_exhausted():
        return None
    try:
        ai = get_client()
        user_msg = f"Email do cliente {customer_name}:\nAssunto: {subject}\n\n{body[:2000]}"
        if category:
            user_msg += f"\n\nCategoria detectada: {category}"
        if shopify_data:
            user_msg += f"\n\nDados Shopify do cliente: {str(shopify_data)[:500]}"

        response = await _call_with_retry(
            lambda: ai.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=600,
                system=AUTO_REPLY_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
        )
        return response.content[0].text.strip()
    except Exception as e:
        _handle_credit_error(e)
        logger.error(f"AI auto-reply failed: {e}")
        return None


async def generate_acknowledgment(customer_name: str) -> str:
    """Simple acknowledgment when AI can't fully resolve."""
    name = customer_name.split()[0] if customer_name else "cliente"
    return (
        f"Oi {name}, tudo bem?\n\n"
        f"Recebemos sua mensagem e ja estamos analisando. "
        f"Nossa equipe vai te responder em ate 24 horas uteis.\n\n"
        f"Equipe Carbon"
    )
```

**Step 2: Hook no gmail.py fetch_emails**

Apos o bloco de AI Triage (linha ~351 do gmail.py), apos `apply_triage_results`, adicionar:

```python
# AI Auto-Reply for eligible tickets
try:
    from app.services.ai_email_responder import should_auto_reply, generate_auto_reply, generate_acknowledgment
    from app.services.triage_service import apply_triage_rules

    # Apply triage rules (Victor's config)
    triage_result = await apply_triage_rules(ticket, db)

    if triage_result.get("auto_reply") or await should_auto_reply(
        ticket.category, ticket.priority, ticket.legal_risk
    ):
        reply_text = await generate_auto_reply(
            subject=email_data["subject"],
            body=email_data["body_text"][:2000],
            customer_name=email_data["from_name"],
            category=ticket.category,
        )
        if reply_text:
            from app.services.gmail_service import send_email as gmail_send
            gmail_send(
                to=email_data["from_email"],
                subject=f"Re: {email_data['subject']}",
                body_text=reply_text,
                thread_id=gmail_thread_id,
                in_reply_to=gmail_message_id,
            )
            # Record as outbound message
            ai_msg = Message(
                ticket_id=ticket.id, type="outbound",
                sender_name="Carbon IA", sender_email=settings.GMAIL_SUPPORT_EMAIL,
                body_text=reply_text, gmail_thread_id=gmail_thread_id,
            )
            db.add(ai_msg)
            ticket.first_response_at = datetime.now(timezone.utc)
            ticket.tags = list(set((ticket.tags or []) + ["ai_auto_reply"]))
            logger.info(f"AI auto-replied to ticket #{ticket.number}")
    elif not triage_result.get("actions") or "queued" in str(triage_result.get("actions")):
        # Nobody online, send acknowledgment
        ack = await generate_acknowledgment(email_data["from_name"])
        from app.services.gmail_service import send_email as gmail_send
        gmail_send(
            to=email_data["from_email"],
            subject=f"Re: {email_data['subject']}",
            body_text=ack,
            thread_id=gmail_thread_id,
            in_reply_to=gmail_message_id,
        )
        ai_msg = Message(
            ticket_id=ticket.id, type="outbound",
            sender_name="Carbon IA", sender_email=settings.GMAIL_SUPPORT_EMAIL,
            body_text=ack, gmail_thread_id=gmail_thread_id,
        )
        db.add(ai_msg)
        ticket.first_response_at = datetime.now(timezone.utc)
        ticket.tags = list(set((ticket.tags or []) + ["ai_ack"]))
except Exception as e:
    logger.warning(f"AI auto-reply skipped: {e}")
```

**Step 3: Commit**

```bash
git add backend/app/services/ai_email_responder.py backend/app/api/gmail.py
git commit -m "feat: AI auto-reply for email tickets (40-50% automation)"
```

---

## Task 6: Dashboard do Lider (backend)

**Files:**
- Modify: `backend/app/api/dashboard.py` (add leader endpoint)

**Step 1: Adicionar endpoint /dashboard/leader**

Adicionar ao final de `backend/app/api/dashboard.py`:

```python
@router.get("/leader")
async def get_leader_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Dashboard do lider: KPIs por agente, presenca, alertas."""
    from app.services.triage_service import get_online_agents, ONLINE_THRESHOLD_MINUTES

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    # All agents
    agents_result = await db.execute(
        select(User).where(User.is_active == True, User.role.in_(["agent", "supervisor", "admin"]))
    )
    all_agents = agents_result.scalars().all()
    online_agents = await get_online_agents(db)
    online_ids = {a.id for a in online_agents}

    agent_stats = []
    for agent in all_agents:
        # Open tickets
        open_q = await db.execute(
            select(func.count()).select_from(Ticket).where(
                Ticket.assigned_to == agent.id,
                Ticket.status.notin_(["resolved", "closed", "archived", "merged"])
            )
        )
        open_count = open_q.scalar()

        # Resolved today
        resolved_today_q = await db.execute(
            select(func.count()).select_from(Ticket).where(
                Ticket.assigned_to == agent.id, Ticket.resolved_at >= today_start
            )
        )
        resolved_today = resolved_today_q.scalar()

        # Resolved this week
        resolved_week_q = await db.execute(
            select(func.count()).select_from(Ticket).where(
                Ticket.assigned_to == agent.id, Ticket.resolved_at >= week_start
            )
        )
        resolved_week = resolved_week_q.scalar()

        # Avg response time (last 7 days)
        avg_resp_q = await db.execute(
            select(
                func.avg(func.extract("epoch", Ticket.first_response_at - Ticket.created_at) / 3600)
            ).where(
                Ticket.assigned_to == agent.id,
                Ticket.first_response_at.isnot(None),
                Ticket.created_at >= today_start - timedelta(days=7),
            )
        )
        avg_resp = round(avg_resp_q.scalar() or 0, 1)

        # Oldest unanswered ticket
        oldest_q = await db.execute(
            select(Ticket.number, Ticket.created_at).where(
                Ticket.assigned_to == agent.id,
                Ticket.status.in_(["open", "in_progress"]),
                Ticket.first_response_at.is_(None),
            ).order_by(Ticket.created_at.asc()).limit(1)
        )
        oldest = oldest_q.first()
        oldest_hours = None
        if oldest:
            oldest_hours = round((datetime.now(timezone.utc) - oldest[1]).total_seconds() / 3600, 1)

        agent_stats.append({
            "id": agent.id, "name": agent.name, "role": agent.role,
            "specialty": agent.specialty,
            "is_online": agent.id in online_ids,
            "last_activity": agent.last_activity_at.isoformat() if agent.last_activity_at else None,
            "open_tickets": open_count,
            "resolved_today": resolved_today,
            "resolved_week": resolved_week,
            "avg_response_hours": avg_resp,
            "oldest_unanswered_hours": oldest_hours,
        })

    # Global alerts
    alerts = []
    total_unassigned_q = await db.execute(
        select(func.count()).select_from(Ticket).where(
            Ticket.assigned_to.is_(None),
            Ticket.status.notin_(["resolved", "closed", "archived", "merged"])
        )
    )
    unassigned = total_unassigned_q.scalar()
    if unassigned > 10:
        alerts.append({"type": "warning", "message": f"{unassigned} tickets sem agente"})
    if len(online_ids) < 2:
        alerts.append({"type": "critical", "message": f"Apenas {len(online_ids)} agente(s) online"})

    # AI stats today
    ai_replied_q = await db.execute(
        select(func.count()).select_from(Message).where(
            Message.sender_name == "Carbon IA",
            Message.created_at >= today_start,
        )
    )
    ai_replied_today = ai_replied_q.scalar()

    return {
        "agents": sorted(agent_stats, key=lambda x: x["resolved_today"], reverse=True),
        "online_count": len(online_ids),
        "total_agents": len(all_agents),
        "alerts": alerts,
        "ai_replies_today": ai_replied_today,
        "unassigned_count": unassigned,
    }
```

**Step 2: Commit**

```bash
git add backend/app/api/dashboard.py
git commit -m "feat: leader dashboard API with per-agent KPIs and alerts"
```

---

## Task 7: Monitor Reclame Aqui

**Files:**
- Create: `backend/app/services/ra_monitor.py`
- Create: `backend/app/api/ra_monitor.py`

**Step 1: Criar ra_monitor.py**

```python
# backend/app/services/ra_monitor.py
"""Reclame Aqui monitor — scrapes new complaints and creates urgent tickets."""
import logging
import httpx
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

RA_LIST_URL = "https://www.reclameaqui.com.br/empresa/carbon-smartwatch/lista-reclamacoes/"


async def fetch_ra_complaints() -> list[dict]:
    """Fetch latest RA complaints via HTTP + parse HTML."""
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            # Try the API endpoint that RA frontend uses
            resp = await client.get(
                "https://iosearch.reclameaqui.com.br/raichu-io-site-search-v1/companies/carbon-smartwatch/complains",
                params={"size": 10, "offset": 0},
                headers={"User-Agent": "Mozilla/5.0"}
            )
            if resp.status_code == 200:
                data = resp.json()
                complaints = []
                for item in data.get("data", {}).get("complains", []):
                    complaints.append({
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "description": item.get("description", "")[:500],
                        "created": item.get("created"),
                        "status": item.get("status"),
                        "user_city": item.get("userCity"),
                        "user_state": item.get("userState"),
                        "url": f"https://www.reclameaqui.com.br/{item.get('url', '')}",
                    })
                return complaints
    except Exception as e:
        logger.error(f"RA monitor fetch failed: {e}")
    return []


async def check_new_complaints(db) -> list[dict]:
    """Check for new RA complaints and create tickets for untracked ones."""
    from sqlalchemy import select
    from app.models.ticket import Ticket

    complaints = await fetch_ra_complaints()
    new_complaints = []

    for complaint in complaints:
        ra_id = str(complaint.get("id", ""))
        if not ra_id:
            continue

        # Check if we already have a ticket for this RA complaint
        existing = await db.execute(
            select(Ticket).where(Ticket.tags.any(f"ra:{ra_id}"))
        )
        if existing.scalars().first():
            continue

        # Check if not responded
        if complaint.get("status") in ("NOT_ANSWERED",):
            new_complaints.append(complaint)

    return new_complaints


async def create_ra_ticket(complaint: dict, db) -> dict:
    """Create an urgent ticket from an RA complaint."""
    from app.models.ticket import Ticket
    from app.models.customer import Customer
    from app.services.ticket_number import get_next_ticket_number
    from datetime import timedelta

    ra_id = str(complaint["id"])
    next_num = await get_next_ticket_number(db)

    ticket = Ticket(
        number=next_num,
        subject=f"[RECLAME AQUI] {complaint['title'][:450]}",
        status="open",
        priority="urgent",
        category="juridico_risco",
        source="reclame_aqui",
        legal_risk=True,
        tags=[f"ra:{ra_id}", "reclame_aqui", "urgente"],
        sla_deadline=datetime.now(timezone.utc) + timedelta(hours=4),
        ai_summary=complaint.get("description", "")[:500],
    )

    # Create placeholder customer
    customer = Customer(
        name=f"Cliente RA #{ra_id}",
        email=f"ra-{ra_id}@reclameaqui.placeholder",
        tags=["reclame_aqui"],
    )
    db.add(customer)
    await db.flush()
    ticket.customer_id = customer.id

    db.add(ticket)
    await db.flush()

    return {"ticket_number": ticket.number, "ra_id": ra_id, "title": complaint["title"]}
```

**Step 2: Criar API endpoint**

```python
# backend/app/api/ra_monitor.py
"""Reclame Aqui monitoring endpoints."""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.ra_monitor import fetch_ra_complaints, check_new_complaints, create_ra_ticket

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ra-monitor", tags=["reclame-aqui"])


@router.get("/complaints")
async def get_ra_complaints(user: User = Depends(get_current_user)):
    """Fetch latest RA complaints."""
    complaints = await fetch_ra_complaints()
    return {"complaints": complaints, "total": len(complaints)}


@router.post("/sync")
async def sync_ra_complaints(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Check for new RA complaints and create urgent tickets."""
    new = await check_new_complaints(db)
    created = []
    for complaint in new:
        try:
            result = await create_ra_ticket(complaint, db)
            created.append(result)
        except Exception as e:
            logger.error(f"Failed to create RA ticket: {e}")

    if created:
        await db.commit()

    return {"new_complaints": len(new), "tickets_created": len(created), "details": created}
```

**Step 3: Registrar router e commit**

```bash
git add backend/app/services/ra_monitor.py backend/app/api/ra_monitor.py
git commit -m "feat: Reclame Aqui monitor — auto-create urgent tickets from new complaints"
```

---

## Task 8: Auto-close + inducao ao fechamento

**Files:**
- Modify: `backend/app/api/tickets.py` (add auto-close logic)

**Step 1: Endpoint de auto-close para tickets parados**

Adicionar no `backend/app/api/tickets.py`:

```python
@router.post("/auto-close-stale")
async def auto_close_stale_tickets(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Auto-close tickets where agent replied and customer didn't respond in 5 days."""
    from datetime import timedelta
    threshold = datetime.now(timezone.utc) - timedelta(days=5)

    # Find tickets where last message is outbound and older than 5 days
    from sqlalchemy.orm import aliased
    subq = (
        select(Message.ticket_id, func.max(Message.created_at).label("last_msg_at"),
               func.max(case((Message.type == "outbound", Message.created_at))).label("last_outbound"))
        .group_by(Message.ticket_id)
        .subquery()
    )

    stale_q = await db.execute(
        select(Ticket).join(subq, Ticket.id == subq.c.ticket_id).where(
            Ticket.status.in_(["waiting", "open", "in_progress"]),
            subq.c.last_outbound.isnot(None),
            subq.c.last_msg_at == subq.c.last_outbound,  # last msg is from agent
            subq.c.last_outbound < threshold,
        )
    )
    stale_tickets = stale_q.scalars().all()

    closed = 0
    for ticket in stale_tickets:
        ticket.status = "resolved"
        ticket.resolved_at = datetime.now(timezone.utc)
        ticket.tags = list(set((ticket.tags or []) + ["auto_closed"]))
        closed += 1

    if closed:
        await db.commit()

    return {"checked": len(stale_tickets), "auto_closed": closed}
```

**Step 2: Commit**

```bash
git add backend/app/api/tickets.py
git commit -m "feat: auto-close stale tickets (5 days no customer reply)"
```

---

## Task 9: Frontend — Tela de Triagem

**Files:**
- Create: `frontend/src/pages/TriagemPage.jsx`
- Modify: `frontend/src/App.jsx` (add route)

Pagina onde o Victor configura as regras de triagem.
Componentes: lista de regras, form de criar/editar, preview de agentes online.
Usar o mesmo padrao visual das outras paginas (SettingsPage, ChatbotFlowsPage).

---

## Task 10: Frontend — Dashboard do Lider

**Files:**
- Create: `frontend/src/pages/LeaderDashboardPage.jsx`
- Modify: `frontend/src/App.jsx` (add route)

Pagina com:
- Cards por agente: nome, online/offline, tickets abertos, resolvidos hoje, tempo medio resposta
- Alertas: tickets sem agente, poucos agentes online, fila crescendo
- Graficos: resolvidos por dia (comparando agentes), SLA compliance
- IA stats: tickets resolvidos por IA hoje, taxa de auto-reply
- Botao de reatribuir ticket (arrastar entre agentes)

---

## Task 11: Frontend — Monitor RA

**Files:**
- Modify: `frontend/src/pages/DashboardPage.jsx` (add RA widget)

Widget no dashboard mostrando:
- Ultimas reclamacoes RA
- Botao "Sincronizar" que chama POST /api/ra-monitor/sync
- Contador de reclamacoes nao respondidas
- Link direto pra cada reclamacao no RA

---

## Ordem de Execucao

1. **Task 1** — Limpar categorias (banco + prompt) — rapido, sem risco
2. **Task 2** — Models novos — base pra tudo
3. **Task 4** — Middleware atividade — simples, habilita deteccao online
4. **Task 3** — API Triagem — core do sistema
5. **Task 5** — IA Auto-Reply — maior impacto (40-50% automacao)
6. **Task 6** — Dashboard Lider backend — KPIs
7. **Task 7** — Monitor RA — urgente pro Pedro
8. **Task 8** — Auto-close — ensina fechamento
9. **Task 9** — Frontend Triagem
10. **Task 10** — Frontend Dashboard Lider
11. **Task 11** — Frontend Monitor RA

## KPIs a monitorar pos-deploy

| KPI | Hoje | Meta 30 dias |
|---|---|---|
| 1a resposta | 58.7h | <2h |
| SLA quebrado | 54% | <15% |
| Tickets sem agente | 393 | 0 |
| Automacao IA | 0% | 40-50% |
| Resolucao por agente/dia | irregular | 15-20 |
| Reabertura pos-IA | n/a | <10% |
| Reclamacoes RA/semana | ~15 | reduzir 50% |
| Tickets >24h sem resposta | centenas | 0 |
