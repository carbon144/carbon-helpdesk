import asyncio
from app.core.database import async_session, engine
from app.models.user import User
from app.core.security import hash_password
from sqlalchemy import select

USERS = [
    {"name": "Pedro Castro", "email": "pedro@carbonsmartwatch.com.br", "role": "super_admin", "password": "Carbon2026!"},
    {"name": "Victor Lima", "email": "victor@carbonsmartwatch.com.br", "role": "admin", "password": "Carbon2026!"},
    {"name": "Tauane Teles", "email": "tauane@carbonsmartwatch.com.br", "role": "supervisor", "password": "Carbon2026!"},
    {"name": "Reinan Coutinho", "email": "reinan@carbonsmartwatch.com.br", "role": "agent", "password": "Carbon2026!"},
    {"name": "Luana", "email": "luana@carbonsmartwatch.com.br", "role": "agent", "password": "Carbon2026!"},
]

async def main():
    async with async_session() as db:
        for u in USERS:
            existing = await db.scalar(select(User).where(User.email == u["email"]))
            if existing:
                print(f"  [SKIP] {u['email']} ja existe (role={existing.role})")
                continue
            user = User(
                name=u["name"],
                email=u["email"],
                password_hash=hash_password(u["password"]),
                role=u["role"],
            )
            db.add(user)
            print(f"  [OK] {u['name']} ({u['email']}) - {u['role']}")
        await db.commit()
    print("Done!")

asyncio.run(main())
