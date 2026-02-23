"""Migration: Add super_admin role and set Pedro as super_admin."""
import asyncio
import asyncpg


async def main():
    conn = await asyncpg.connect(
        host="postgres", port=5432, user="carbon",
        password="carbon_secret_2026", database="carbon_helpdesk"
    )

    # 1. Add super_admin to user_role enum
    try:
        await conn.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'super_admin' BEFORE 'admin'")
        print("✓ Adicionado 'super_admin' ao enum user_role")
    except Exception as e:
        print(f"Enum já existe ou erro: {e}")

    # 2. Set Pedro as super_admin
    r = await conn.execute(
        "UPDATE users SET role='super_admin' WHERE email='pedro@carbonsmartwatch.com.br'"
    )
    print(f"✓ Pedro atualizado para super_admin: {r}")

    # 3. Show all users with roles
    rows = await conn.fetch("SELECT name, email, role FROM users ORDER BY name")
    print(f"\nUsuários ({len(rows)}):")
    for row in rows:
        print(f"  {row['name']} ({row['email']}) - {row['role']}")

    await conn.close()


asyncio.run(main())
