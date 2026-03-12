"""
Classificação IA Batch — Analisa todos os tickets abertos e classifica:
- resolvido: já teve resposta satisfatória, caso fechado
- precisa_resposta: cliente esperando resposta
- spam: email irrelevante (notificações, newsletters, etc)
- Também re-triagem com categoria correta (substituindo fallback por keywords)

Uso: docker exec carbon-backend python -m scripts.classify_tickets_batch [--dry-run] [--limit N] [--batch-size N]
"""
import asyncio
import json
import logging
import sys
import time
from anthropic import Anthropic

# ── Setup logging ──
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("classify_batch")

# ── Config ──
MODEL = "claude-haiku-4-5-20251001"
BATCH_SIZE = 10  # tickets per batch (parallelism)
RATE_LIMIT_DELAY = 0.5  # seconds between API calls
MAX_MSG_PER_TICKET = 4  # max messages to include
MAX_MSG_CHARS = 400  # max chars per message body


CLASSIFY_PROMPT = """Você é o classificador do suporte da Carbon Smartwatch (relogios smartwatch brasileiros).

Analise o ticket abaixo (subject + mensagens) e retorne APENAS JSON válido:

{
  "status": "resolvido | precisa_resposta | spam",
  "category": "meu_pedido | garantia | reenvio | financeiro | duvida | reclamacao",
  "priority": "low | medium | high | urgent",
  "sentiment": "positive | neutral | negative | angry",
  "legal_risk": true ou false,
  "tags": ["tags relevantes"],
  "confidence": 0.0 a 1.0,
  "summary": "briefing curto: problema → próximo passo",
  "reason": "1 frase explicando por que classificou assim"
}

REGRAS DE STATUS:
- "resolvido": a equipe JÁ respondeu E o cliente não voltou a reclamar, OU o assunto é uma notificação/confirmação que não precisa de resposta
- "precisa_resposta": cliente fez uma pergunta/reclamação/pedido e NÃO recebeu resposta, ou recebeu mas voltou com novo problema
- "spam": emails automáticos, newsletters, notificações do sistema, emails de marketing, emails que não são de clientes

CATEGORIAS:
- meu_pedido: quer saber onde está o pedido, rastreio, nota fiscal, cancelar, pedido incompleto
- garantia: defeito, troca, devolução, produto errado, carregador quebrado, assistência
- reenvio: produto extraviado, não chegou E quer que envie de novo
- financeiro: estorno, reembolso, chargeback, dúvida pagamento
- duvida: pré-venda, como usar, funcionalidades, elogio, sugestão
- reclamacao: insatisfação, golpe, menciona GUACU, propaganda enganosa

CONTEXTO:
- GUACU NEGOCIOS DIGITAIS LTDA = Carbon Smartwatch (mesma empresa)
- Houve atrasos jan-fev 2026 (importação). Já corrigido.
- Garantia: 12 meses, troca direta, sem assistência técnica
- Se email é da própria Carbon/sistema (ex: "você tem tickets que não viu") → spam

PRIORIDADE:
- urgent: PROCON, chargeback, advogado, Reclame Aqui, juizado
- high: defeito grave, cliente reincidente, produto não chegou, reclamação forte
- medium: trocas, problemas técnicos, dúvidas sobre entrega
- low: dúvidas simples, elogios, feedback

legal_risk = true se menciona: PROCON, processo, advogado, Reclame Aqui, chargeback, danos morais

TAGS possíveis: guacu, procon, advogado, reclame_aqui, chargeback, mau_uso, carregador, defeito, troca, nf, reembolso, reincidente"""


async def get_db():
    """Get async DB session."""
    from app.core.database import async_session
    return async_session()


def build_ticket_text(ticket_row, messages) -> str:
    """Build text representation of a ticket for classification."""
    parts = [f"SUBJECT: {ticket_row['subject'] or '(sem assunto)'}"]

    for i, msg in enumerate(messages[:MAX_MSG_PER_TICKET]):
        direction = "CLIENTE" if msg["type"] == "inbound" else "EQUIPE"
        body = (msg["body_text"] or msg["body_html"] or "")[:MAX_MSG_CHARS]
        parts.append(f"\nMSG {i+1} ({direction}):\n{body}")

    return "\n".join(parts)


def parse_response(text: str) -> dict | None:
    """Parse JSON from Claude response."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse JSON: {text[:200]}")
        return None


async def classify_ticket(client: Anthropic, ticket_text: str) -> dict | None:
    """Call Haiku to classify a single ticket."""
    try:
        response = await asyncio.to_thread(
            client.messages.create,
            model=MODEL,
            max_tokens=300,
            system=CLASSIFY_PROMPT,
            messages=[{"role": "user", "content": ticket_text}],
        )
        return parse_response(response.content[0].text)
    except Exception as e:
        logger.error(f"API error: {e}")
        return None


async def run(dry_run=False, limit=0, batch_size=BATCH_SIZE):
    """Main classification loop."""
    from sqlalchemy import text

    api_key = None
    try:
        from app.core.config import settings
        api_key = settings.ANTHROPIC_API_KEY
    except Exception:
        import os
        api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found")
        return

    client = Anthropic(api_key=api_key)

    async with (await get_db()) as db:
        # Get all open tickets
        q = "SELECT id, subject, status, category, priority FROM tickets WHERE status IN ('open', 'waiting') ORDER BY created_at ASC"
        if limit > 0:
            q += f" LIMIT {limit}"
        result = await db.execute(text(q))
        tickets = [dict(r._mapping) for r in result.fetchall()]
        total = len(tickets)
        logger.info(f"Found {total} tickets to classify")

        stats = {"resolvido": 0, "precisa_resposta": 0, "spam": 0, "errors": 0, "category_changed": 0}
        start_time = time.time()

        for i in range(0, total, batch_size):
            batch = tickets[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total + batch_size - 1) // batch_size
            logger.info(f"Batch {batch_num}/{total_batches} ({len(batch)} tickets)")

            for ticket in batch:
                tid = str(ticket["id"])

                # Get messages for this ticket
                msg_result = await db.execute(text(
                    "SELECT type, body_text, body_html, created_at FROM messages "
                    "WHERE ticket_id = :tid ORDER BY created_at ASC"
                ), {"tid": tid})
                messages = [dict(r._mapping) for r in msg_result.fetchall()]

                ticket_text = build_ticket_text(ticket, messages)
                result = await classify_ticket(client, ticket_text)

                if not result:
                    stats["errors"] += 1
                    continue

                status = result.get("status", "precisa_resposta")
                new_category = result.get("category", ticket["category"])
                stats[status] = stats.get(status, 0) + 1
                if new_category != ticket["category"]:
                    stats["category_changed"] += 1

                if dry_run:
                    logger.info(
                        f"  [DRY] #{tid[:8]} | {ticket['category']}→{new_category} | "
                        f"{ticket['status']}→{status} | {result.get('summary', '')[:60]}"
                    )
                else:
                    # Map status
                    db_status = {
                        "resolvido": "resolved",
                        "precisa_resposta": "open",
                        "spam": "resolved",
                    }.get(status, "open")

                    update_fields = {
                        "status": db_status,
                        "category": new_category,
                        "ai_category": new_category,
                        "priority": result.get("priority", ticket["priority"]),
                        "sentiment": result.get("sentiment"),
                        "legal_risk": result.get("legal_risk", False),
                        "ai_confidence": result.get("confidence", 0.5),
                        "ai_summary": result.get("summary"),
                    }

                    # Tags
                    new_tags = result.get("tags", [])
                    if status == "spam":
                        new_tags.append("spam")

                    # Resolved_at for resolved/spam
                    resolved_clause = ""
                    if db_status == "resolved":
                        resolved_clause = ", resolved_at = NOW()"

                    await db.execute(text(
                        f"UPDATE tickets SET "
                        f"status = :status, category = :category, ai_category = :ai_category, "
                        f"priority = :priority, sentiment = :sentiment, legal_risk = :legal_risk, "
                        f"ai_confidence = :ai_confidence, ai_summary = :ai_summary, "
                        f"tags = :tags{resolved_clause} "
                        f"WHERE id = :tid"
                    ), {
                        **update_fields,
                        "tags": new_tags,
                        "tid": tid,
                    })

                    logger.info(
                        f"  #{tid[:8]} | {ticket['category']}→{new_category} | "
                        f"{status} | p:{result.get('priority')} | {result.get('summary', '')[:60]}"
                    )

                await asyncio.sleep(RATE_LIMIT_DELAY)

            # Commit after each batch
            if not dry_run:
                await db.commit()
                logger.info(f"  Batch {batch_num} committed")

        elapsed = time.time() - start_time
        logger.info(f"\n{'='*60}")
        logger.info(f"DONE in {elapsed:.0f}s ({total} tickets)")
        logger.info(f"  resolvido:        {stats['resolvido']}")
        logger.info(f"  precisa_resposta:  {stats['precisa_resposta']}")
        logger.info(f"  spam:             {stats['spam']}")
        logger.info(f"  category_changed: {stats['category_changed']}")
        logger.info(f"  errors:           {stats['errors']}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    limit = 0
    batch_size = BATCH_SIZE

    for arg in sys.argv[1:]:
        if arg.startswith("--limit"):
            idx = sys.argv.index(arg)
            if idx + 1 < len(sys.argv):
                limit = int(sys.argv[idx + 1])
        if arg.startswith("--batch-size"):
            idx = sys.argv.index(arg)
            if idx + 1 < len(sys.argv):
                batch_size = int(sys.argv[idx + 1])

    if dry_run:
        logger.info("=== DRY RUN MODE (no changes will be made) ===")

    asyncio.run(run(dry_run=dry_run, limit=limit, batch_size=batch_size))
