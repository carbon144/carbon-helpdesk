"""Reclame Aqui monitor — scrapes complaints via Playwright (bypasses Cloudflare)."""
import logging
import json
import re
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

RA_COMPANY_SLUG = "carbon-relogios-inteligentes"
RA_LIST_URL = f"https://www.reclameaqui.com.br/empresa/{RA_COMPANY_SLUG}/lista-reclamacoes/"
RA_COMPANY_URL = f"https://www.reclameaqui.com.br/empresa/{RA_COMPANY_SLUG}/"

# RA internal API that the frontend JS calls after Cloudflare challenge
RA_API_URL = "https://iosearch.reclameaqui.com.br/raichu-io-site-search-v1/companies/{slug}/complains"


async def fetch_ra_complaints(limit: int = 10) -> list[dict]:
    """Fetch latest RA complaints using Playwright to bypass Cloudflare."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
        return []

    complaints = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process",
                ]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720},
            )
            page = await context.new_page()

            # Intercept the API call that RA frontend makes
            api_data = []

            async def handle_response(response):
                if "complains" in response.url and response.status == 200:
                    try:
                        data = await response.json()
                        api_data.append(data)
                    except Exception:
                        pass

            page.on("response", handle_response)

            # Navigate to complaints list — Cloudflare challenge auto-resolves in browser
            await page.goto(RA_LIST_URL, wait_until="networkidle", timeout=45000)

            # Wait for complaints to load (either via API intercept or DOM)
            await page.wait_for_timeout(5000)

            # Try API intercepted data first
            if api_data:
                data = api_data[0]
                for item in data.get("data", {}).get("complains", data.get("complains", [])):
                    complaints.append(_parse_api_complaint(item))
            else:
                # Fallback: parse from DOM
                complaints = await _parse_dom_complaints(page, limit)

            await browser.close()

    except Exception as e:
        logger.error(f"RA Playwright scrape failed: {e}")

    return complaints[:limit]


async def fetch_ra_reputation() -> dict | None:
    """Fetch RA company reputation score."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--single-process"]
            )
            page = await browser.new_page()
            await page.goto(RA_COMPANY_URL, wait_until="networkidle", timeout=45000)
            await page.wait_for_timeout(3000)

            reputation = {}

            # Try to extract reputation score from the page
            try:
                score_el = await page.query_selector('[data-testid="reputation-score"], .reputation-score, .score')
                if score_el:
                    reputation["score"] = await score_el.inner_text()
            except Exception:
                pass

            # Try to get stats from the page
            try:
                stats_text = await page.inner_text("body")
                # Look for patterns like "6.9" rating, "respondidas", etc.
                rating_match = re.search(r'(\d+[.,]\d+)\s*/\s*10', stats_text)
                if rating_match:
                    reputation["rating"] = rating_match.group(1)

                responded_match = re.search(r'(\d+[.,]\d+)%.*?respondidas', stats_text, re.IGNORECASE)
                if responded_match:
                    reputation["response_rate"] = responded_match.group(1) + "%"

                resolved_match = re.search(r'(\d+[.,]\d+)%.*?resolvidas', stats_text, re.IGNORECASE)
                if resolved_match:
                    reputation["resolution_rate"] = resolved_match.group(1) + "%"

                would_buy_match = re.search(r'(\d+[.,]\d+)%.*?comprar', stats_text, re.IGNORECASE)
                if would_buy_match:
                    reputation["would_buy_again"] = would_buy_match.group(1) + "%"
            except Exception:
                pass

            await browser.close()
            return reputation if reputation else None

    except Exception as e:
        logger.error(f"RA reputation fetch failed: {e}")
        return None


def _parse_api_complaint(item: dict) -> dict:
    """Parse a complaint from RA API response."""
    ra_id = item.get("id") or item.get("complainId") or ""
    title = item.get("title") or item.get("complaintTitle") or ""
    description = item.get("description") or item.get("complaintDescription") or ""
    created = item.get("created") or item.get("createDate") or ""
    status = item.get("status") or item.get("complaintStatus") or ""
    url_slug = item.get("url") or ""

    return {
        "id": str(ra_id),
        "title": title[:500],
        "description": description[:500],
        "created": created,
        "status": status,
        "user_city": item.get("userCity", ""),
        "user_state": item.get("userState", ""),
        "url": f"https://www.reclameaqui.com.br/{url_slug}" if url_slug and not url_slug.startswith("http") else url_slug,
        "answered": status not in ("NOT_ANSWERED", "CREATED", ""),
    }


async def _parse_dom_complaints(page, limit: int) -> list[dict]:
    """Fallback: parse complaints from the page DOM."""
    complaints = []
    try:
        # RA uses different selectors depending on version
        selectors = [
            'a[href*="/reclamacao/"]',
            '[data-testid="complaint-item"]',
            '.complaint-item',
            '.sc-1pe7b5t-0',  # styled-component class
        ]

        items = []
        for sel in selectors:
            items = await page.query_selector_all(sel)
            if items:
                break

        for item in items[:limit]:
            try:
                href = await item.get_attribute("href") or ""
                text = await item.inner_text()
                lines = [l.strip() for l in text.split("\n") if l.strip()]

                title = lines[0] if lines else "Sem título"
                # Extract RA ID from URL
                ra_id_match = re.search(r'/reclamacao/[^/]*?_([a-zA-Z0-9]+)/?$', href)
                ra_id = ra_id_match.group(1) if ra_id_match else href.split("/")[-2] if "/" in href else ""

                complaints.append({
                    "id": ra_id,
                    "title": title[:500],
                    "description": " ".join(lines[1:3])[:500] if len(lines) > 1 else "",
                    "created": "",
                    "status": "UNKNOWN",
                    "user_city": "",
                    "user_state": "",
                    "url": f"https://www.reclameaqui.com.br{href}" if href.startswith("/") else href,
                    "answered": False,
                })
            except Exception:
                continue

    except Exception as e:
        logger.warning(f"DOM parsing failed: {e}")

    return complaints


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

        # Only track unanswered ones (or all if status unknown)
        if complaint.get("answered") and complaint.get("status") not in ("UNKNOWN", ""):
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

    # Try to find existing RA placeholder customer or create one
    ra_email = f"ra-{ra_id}@reclameaqui.placeholder"
    existing_customer = await db.execute(
        select(Customer).where(Customer.email == ra_email)
    )
    customer = existing_customer.scalars().first()

    if not customer:
        customer = Customer(
            name=f"Cliente Reclame Aqui",
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
        ai_summary=complaint.get("description", "")[:500],
        customer_id=customer.id,
    )
    db.add(ticket)
    await db.flush()

    # Add complaint text as first message
    if complaint.get("description"):
        msg = Message(
            ticket_id=ticket.id,
            type="inbound",
            sender_name="Cliente Reclame Aqui",
            sender_email=ra_email,
            body_text=f"[Reclamação no Reclame Aqui]\n\n{complaint['title']}\n\n{complaint['description']}\n\nLink: {complaint.get('url', '')}",
        )
        db.add(msg)

    return {
        "ticket_number": ticket.number,
        "ra_id": ra_id,
        "title": complaint["title"],
        "url": complaint.get("url", ""),
    }
