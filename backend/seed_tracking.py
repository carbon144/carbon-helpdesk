"""Remove fake tracking demo data from tickets."""
import asyncio
import asyncpg

FAKE_CODES = [
    "NX123456789BR", "NX987654321BR", "YT2312345678901",
    "LP00123456789", "NX555666777BR", "NX111222333BR", "NX777333111BR",
    "NX555888222BR",
]

async def main():
    conn = await asyncpg.connect(host="postgres", port=5432, user="carbon", password="carbon_secret_2026", database="carbon_helpdesk")

    for code in FAKE_CODES:
        r = await conn.execute(
            "UPDATE tickets SET tracking_code='', tracking_status='', tracking_data=NULL WHERE tracking_code=$1", code
        )
        print(f"Limpando {code}: {r}")

    rows = await conn.fetch("SELECT number, tracking_code FROM tickets WHERE tracking_code != '' AND tracking_code IS NOT NULL ORDER BY number")
    print(f"\nTickets com rastreio real: {len(rows)}")
    for row in rows:
        print(f"  #{row['number']}: {row['tracking_code']}")

    await conn.close()

asyncio.run(main())
