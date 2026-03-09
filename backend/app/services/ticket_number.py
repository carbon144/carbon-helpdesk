"""Atomic ticket number generation using PostgreSQL sequence."""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def init_ticket_sequence(conn):
    """Create and sync the ticket_number_seq sequence on startup.

    Must be called inside an engine.begin() block (raw connection, not session).
    """
    # Create sequence if it doesn't exist
    await conn.execute(text("CREATE SEQUENCE IF NOT EXISTS ticket_number_seq START WITH 1001"))

    # Sync sequence to current MAX(number) + 1
    await conn.execute(text("""
        SELECT setval('ticket_number_seq', COALESCE(
            (SELECT MAX(number) FROM tickets), 1000
        ))
    """))


async def get_next_ticket_number(db: AsyncSession) -> int:
    """Get the next ticket number atomically using a PostgreSQL sequence.

    If the sequence is out of sync (number already exists), re-syncs and retries.
    """
    for _ in range(3):
        result = await db.execute(text("SELECT nextval('ticket_number_seq')"))
        num = result.scalar()
        # Check if this number already exists (handles desync)
        exists = await db.execute(
            text("SELECT 1 FROM tickets WHERE number = :n"), {"n": num}
        )
        if not exists.scalar():
            return num
        # Re-sync sequence to max and retry
        await db.execute(text("""
            SELECT setval('ticket_number_seq', COALESCE(
                (SELECT MAX(number) FROM tickets), 1000
            ))
        """))
    # Final fallback: MAX + 1
    result = await db.execute(text("SELECT COALESCE(MAX(number), 1000) + 1 FROM tickets"))
    return result.scalar()
