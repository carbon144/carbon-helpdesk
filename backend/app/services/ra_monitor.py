"""Reclame Aqui monitor — fetches complaints via Google Search (RA uses Cloudflare Turnstile)."""
import logging
import re
import html
from datetime import datetime, timezone
from urllib.parse import quote_plus

import httpx

logger = logging.getLogger(__name__)

RA_COMPANY_SLUG = "carbon-smartwatch"
RA_BASE = "https://www.reclameaqui.com.br"

# Google search query to find recent RA complaints
GOOGLE_SEARCH_URL = "https://www.google.com/search"
SEARCH_QUERY = f'site:reclameaqui.com.br/carbon-smartwatch/ -lista-reclamacoes -sobre -empresa'

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


def _extract_ra_id_from_url(url: str) -> str:
    """Extract RA complaint ID from URL like /carbon-smartwatch/titulo_ABC123XYZ/"""
    match = re.search(r'_([a-zA-Z0-9_-]{8,})/?$', url)
    return match.group(1) if match else ""


def _clean_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


async def fetch_ra_complaints(limit: int = 10) -> list[dict]:
    """Fetch latest RA complaints via Google Search results."""
    complaints = []

    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(
                GOOGLE_SEARCH_URL,
                params={
                    "q": SEARCH_QUERY,
                    "num": min(limit + 5, 20),  # extra to filter non-complaints
                    "hl": "pt-BR",
                },
                headers=HEADERS,
            )

            if resp.status_code != 200:
                logger.warning(f"Google search returned {resp.status_code}")
                return []

            body = resp.text

            # Parse Google search results — extract URLs and titles
            # Google wraps results in <a href="/url?q=..." blocks
            # or directly in <a href="https://..." blocks
            results = re.findall(
                r'<a[^>]+href="(?:/url\?q=)?'
                r'(https?://(?:www\.)?reclameaqui\.com\.br/carbon-smartwatch/[^"&]+)'
                r'"[^>]*>.*?</a>',
                body,
                re.DOTALL,
            )

            # Also try the data-href pattern
            results += re.findall(
                r'data-href="(https?://(?:www\.)?reclameaqui\.com\.br/carbon-smartwatch/[^"]+)"',
                body,
            )

            # Deduplicate
            seen_urls = set()
            unique_results = []
            for url in results:
                # Clean URL
                url = url.split("&")[0]  # Remove Google tracking params
                if url not in seen_urls:
                    seen_urls.add(url)
                    unique_results.append(url)

            for url in unique_results:
                # Skip non-complaint pages
                if "/lista-reclamacoes" in url or "/sobre/" in url or "/empresa/" in url:
                    continue

                ra_id = _extract_ra_id_from_url(url)
                if not ra_id:
                    continue

                # Extract title from the URL slug
                slug_match = re.search(r'/carbon-smartwatch/([^_]+)_', url)
                title = slug_match.group(1).replace("-", " ").title() if slug_match else "Reclamação"

                complaints.append({
                    "id": ra_id,
                    "title": title[:500],
                    "description": "",
                    "created": "",
                    "status": "UNKNOWN",
                    "url": url,
                    "answered": False,
                })

                if len(complaints) >= limit:
                    break

            # Try to extract snippets/descriptions from Google results
            # Match title + snippet blocks
            snippet_blocks = re.findall(
                r'<h3[^>]*>(.*?)</h3>.*?(?:<div[^>]*class="[^"]*VwiC3b[^"]*"[^>]*>|<span[^>]*>)(.*?)</(?:div|span)>',
                body,
                re.DOTALL,
            )

            for block_title, snippet in snippet_blocks:
                clean_title = _clean_html(block_title)
                clean_snippet = _clean_html(snippet)

                # Match to existing complaints by title similarity
                for c in complaints:
                    title_words = set(c["title"].lower().split())
                    block_words = set(clean_title.lower().split())
                    if len(title_words & block_words) >= 2:
                        if clean_title and "Carbon Smartwatch" in clean_title:
                            c["title"] = clean_title.replace(" - Carbon Smartwatch - Reclame AQUI", "").replace(" - Carbon Smartwatch - Reclame Aqui", "").strip()
                        if clean_snippet:
                            c["description"] = clean_snippet[:500]
                        break

    except Exception as e:
        logger.error(f"RA Google search failed: {e}")

    return complaints


async def fetch_ra_reputation() -> dict | None:
    """Fetch RA reputation data via Google Search snippet."""
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(
                GOOGLE_SEARCH_URL,
                params={
                    "q": "reclameaqui.com.br carbon smartwatch reputação nota",
                    "num": 5,
                    "hl": "pt-BR",
                },
                headers=HEADERS,
            )

            if resp.status_code != 200:
                return None

            body = resp.text
            reputation = {}

            # Extract rating from Google snippet
            rating_match = re.search(r'nota?\s*(?:é\s*)?(\d+[.,]\d+)\s*/?\s*10', body, re.IGNORECASE)
            if rating_match:
                reputation["rating"] = rating_match.group(1)

            # Look for reputation level (Regular, Bom, Ótimo, etc.)
            level_match = re.search(r'reputação\s+(\w+)', body, re.IGNORECASE)
            if level_match:
                reputation["level"] = level_match.group(1).capitalize()

            # Response rate
            resp_match = re.search(r'(\d+[.,]\d+)%\s*(?:de\s*)?resposta', body, re.IGNORECASE)
            if resp_match:
                reputation["response_rate"] = resp_match.group(1) + "%"

            return reputation if reputation else None

    except Exception as e:
        logger.error(f"RA reputation fetch failed: {e}")
        return None


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

        # Check if we already have a ticket with this RA ID in tags
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

    # Use a single shared RA customer (not one per complaint)
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

    # Add complaint as first message
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
