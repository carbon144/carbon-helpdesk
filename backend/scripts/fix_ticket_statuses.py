"""Check Gmail threads for SENT replies and update ticket statuses."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def fix():
    from app.services.gmail_service import get_gmail_service
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import text
    from app.core.config import settings

    engine = create_async_engine(settings.DATABASE_URL)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    service = get_gmail_service()

    async with Session() as db:
        r = await db.execute(text("SELECT DISTINCT gmail_thread_id FROM messages WHERE gmail_thread_id IS NOT NULL"))
        tids = [row[0] for row in r.fetchall()]
        print(f"Threads to check: {len(tids)}")

        replied = set()
        for i, tid in enumerate(tids):
            try:
                t = service.users().threads().get(userId="me", id=tid, format="metadata", metadataHeaders=["From"]).execute()
                for m in t.get("messages", []):
                    if "SENT" in m.get("labelIds", []):
                        replied.add(tid)
                        break
            except Exception:
                pass
            if (i + 1) % 500 == 0:
                print(f"  checked {i+1}/{len(tids)}, replied so far: {len(replied)}")

        print(f"Threads with our SENT reply: {len(replied)} / {len(tids)}")

        updated = 0
        for tid in replied:
            r2 = await db.execute(
                text("UPDATE tickets SET status = 'waiting' WHERE id IN (SELECT DISTINCT ticket_id FROM messages WHERE gmail_thread_id = :tid) AND status = 'open'"),
                {"tid": tid},
            )
            updated += r2.rowcount
        await db.commit()
        print(f"Tickets marked waiting (already replied): {updated}")

        # Also close very old tickets (> 30 days) as resolved
        r3 = await db.execute(
            text("UPDATE tickets SET status = 'resolved', resolved_at = now() WHERE status = 'open' AND received_at < now() - interval '30 days'")
        )
        print(f"Tickets auto-resolved (>30 days old): {r3.rowcount}")
        await db.commit()

        # Final counts
        r4 = await db.execute(text("SELECT status, count(*) FROM tickets GROUP BY status ORDER BY count DESC"))
        print("=== FINAL STATUS ===")
        for row in r4.fetchall():
            print(f"  {row[0]}: {row[1]}")

asyncio.run(fix())
