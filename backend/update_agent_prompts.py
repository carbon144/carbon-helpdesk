"""Update AI agent prompts in production DB.
Usage: docker exec carbon-backend python update_agent_prompts.py
Or locally: python update_agent_prompts.py
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.services.seed_ai_agents import AGENTS


async def update_prompts():
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://carbon:CarbonMail2026@localhost:5432/carbon_helpdesk"
    )
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        for agent_data in AGENTS:
            name = agent_data["name"]
            result = await db.execute(
                text("UPDATE ai_agents SET system_prompt = :prompt, few_shot_examples = :examples WHERE name = :name"),
                {
                    "prompt": agent_data["system_prompt"],
                    "examples": json.dumps(agent_data.get("few_shot_examples", [])),
                    "name": name,
                }
            )
            if result.rowcount > 0:
                print(f"  Updated: {name}")
            else:
                print(f"  NOT FOUND: {name} (skipped)")

        await db.commit()
        print("\nAll agent prompts updated successfully.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(update_prompts())
