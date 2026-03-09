"""Reclame Aqui monitor — fetches complaints via DuckDuckGo Search."""
import logging
import re
import html as htmlmod
from datetime import datetime, timezone
from urllib.parse import unquote

import httpx

logger = logging.getLogger(__name__)

RA_COMPANY_SLUG = "carbon-smartwatch"
DDG_URL = "https://html.duckduckgo.com/html/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html",
    "Accept-Language": "pt-BR,pt;q=0.9",
}


def _extract_ra_id_from_url(url: str) -> str:
    """Extract RA complaint ID from URL like /carbon-smartwatch/titulo_ABC123XYZ/"""
    match = re.search(r'_([a-zA-Z0-9_-]{8,})/?$', url)
    return match.group(1) if match else ""


def _clean(text: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', text)
    text = htmlmod.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


async def fetch_ra_complaints(limit: int = 10) -> list[dict]:
    """Fetch RA complaints via DuckDuckGo search."""
    complaints = []

    queries = [
        f"site:reclameaqui.com.br/carbon-smartwatch/ reclamação 2026",
        f"site:reclameaqui.com.br/carbon-smartwatch/ defeito",
        f"site:reclameaqui.com.br/carbon-smartwatch/ não recebi",
    ]

    seen_ids = set()

    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            for query in queries:
                if len(complaints) >= limit:
                    break

                resp = await client.post(
                    DDG_URL,
                    data={"q": query, "b": ""},
                    headers=HEADERS,
                )

                if resp.status_code != 200:
                    continue

                body = resp.text

                # Extract URLs from DDG uddg redirect params
                uddg_urls = re.findall(r'uddg=([^&"]+)', body)
                for encoded_url in uddg_urls:
                    url = unquote(encoded_url)

                    # Only individual complaints (not empresa/lista pages)
                    if "/empresa/" in url or "/lista-reclamacoes" in url or "/sobre/" in url:
                        continue

                    if f"reclameaqui.com.br/{RA_COMPANY_SLUG}/" not in url:
                        continue

                    ra_id = _extract_ra_id_from_url(url)
                    if not ra_id or ra_id in seen_ids:
                        continue

                    seen_ids.add(ra_id)

                    # Extract title from URL slug
                    slug_match = re.search(rf'/{RA_COMPANY_SLUG}/([^_]+)_', url)
                    title = slug_match.group(1).replace("-", " ").title() if slug_match else "Reclamação"

                    complaints.append({
                        "id": ra_id,
                        "title": title[:500],
                        "description": "",
                        "created": "",
                        "status": "UNKNOWN",
                        "url": url.rstrip("/") + "/",
                        "answered": False,
                    })

                    if len(complaints) >= limit:
                        break

                # Extract titles/snippets from result blocks
                result_blocks = re.findall(
                    r'class="result__a"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</(?:td|div|span)>',
                    body,
                    re.DOTALL,
                )

                for block_title, snippet in result_blocks:
                    clean_title = _clean(block_title)
                    clean_snippet = _clean(snippet)

                    # Match to existing complaints
                    for c in complaints:
                        if c["description"]:
                            continue
                        title_words = set(c["title"].lower().split())
                        block_words = set(clean_title.lower().split())
                        if len(title_words & block_words) >= 2:
                            real_title = re.sub(
                                r'\s*-\s*Carbon Smartwatch\s*-\s*Reclame\s*(AQUI|Aqui).*$',
                                '', clean_title
                            ).strip()
                            if real_title:
                                c["title"] = real_title
                            if clean_snippet:
                                c["description"] = clean_snippet[:500]
                            break

    except Exception as e:
        logger.error(f"RA search failed: {e}")

    return complaints[:limit]


async def fetch_ra_reputation() -> dict | None:
    """Return cached reputation data (RA site blocked by Cloudflare)."""
    # Hardcoded from session 19 analysis (1,518 complaints, rating 6.9/10)
    # TODO: update periodically when accessible
    return {
        "rating": "6.9",
        "level": "Regular",
        "total_complaints": "1518+",
        "response_rate": "98%",
        "resolution_rate": "72%",
        "would_buy_again": "47%",
        "last_updated": "2026-03-09",
    }


async def check_new_complaints(db) -> list[dict]:
    """Check for new RA complaints not yet tracked as tickets."""
    from sqlalchemy import select, text
    from app.models.ticket import Ticket

    complaints = await fetch_ra_complaints(limit=10)
    new_complaints = []

    for complaint in complaints:
        ra_id = complaint.get("id", "")
        if not ra_id:
            continue

        tag = f"ra:{ra_id}"
        existing = await db.execute(
            select(Ticket).where(
                text("tags @> ARRAY[:tag]::varchar[]").bindparams(tag=tag)
            )
        )
        if existing.scalars().first():
            continue

        new_complaints.append(complaint)

    return new_complaints


async def create_ra_ticket(complaint: dict, db) -> dict:
    """Create an urgent ticket from an RA complaint."""
    from app.models.ticket import Ticket
    from app.models.customer import Customer
    from app.models.message import Message
    from app.services.ticket_number import get_next_ticket_number
    from datetime import timedelta
    from sqlalchemy import select

    ra_id = str(complaint["id"])
    next_num = await get_next_ticket_number(db)

    ra_email = "reclameaqui@carbon.placeholder"
    existing_customer = await db.execute(
        select(Customer).where(Customer.email == ra_email)
    )
    customer = existing_customer.scalars().first()

    if not customer:
        customer = Customer(
            name="Cliente Reclame Aqui",
            email=ra_email,
            tags=["reclame_aqui"],
            risk_score=8.0,
        )
        db.add(customer)
        await db.flush()

    ticket = Ticket(
        number=next_num,
        subject=f"[RECLAME AQUI] {complaint['title'][:450]}",
        status="open",
        priority="urgent",
        category="reclamacao",
        source="reclame_aqui",
        legal_risk=True,
        tags=[f"ra:{ra_id}", "reclame_aqui", "urgente"],
        sla_deadline=datetime.now(timezone.utc) + timedelta(hours=4),
        ai_summary=complaint.get("description", "")[:500] or complaint.get("title", ""),
        customer_id=customer.id,
    )
    db.add(ticket)
    await db.flush()

    body_parts = [f"[Reclamação no Reclame Aqui]\n\nTítulo: {complaint['title']}"]
    if complaint.get("description"):
        body_parts.append(f"\n{complaint['description']}")
    body_parts.append(f"\nLink: {complaint.get('url', '')}")

    msg = Message(
        ticket_id=ticket.id,
        type="inbound",
        sender_name="Cliente Reclame Aqui",
        sender_email=ra_email,
        body_text="\n".join(body_parts),
    )
    db.add(msg)

    return {
        "ticket_number": ticket.number,
        "ra_id": ra_id,
        "title": complaint["title"],
        "url": complaint.get("url", ""),
    }
