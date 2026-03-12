"""Update AI agent prompts in production DB with Lyvia-validated rules.

Usage: python -m scripts.update_agent_prompts_v2
Run from backend/ directory.
"""

import asyncio
import logging
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Import agent definitions (same source as seed)
from app.services.seed_ai_agents import AGENTS


# Production DB — same pattern as other scripts
DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://carbon:CarbonMail2026@localhost:5432/carbon_helpdesk"
)


async def main():
    """Update system_prompt for each agent in ai_agents table."""
    # Parse asyncpg-compatible URL
    db_url = DB_URL.replace("postgresql://", "postgres://").replace("postgresql+asyncpg://", "postgres://")

    logger.info(f"Connecting to DB...")
    conn = await asyncpg.connect(db_url)

    try:
        # Get current agents from DB
        rows = await conn.fetch("SELECT id, name, system_prompt FROM ai_agents")
        db_agents = {row["name"]: row for row in rows}
        logger.info(f"Found {len(db_agents)} agents in DB: {list(db_agents.keys())}")

        updated = 0
        for agent_data in AGENTS:
            name = agent_data["name"]
            new_prompt = agent_data["system_prompt"]

            if name not in db_agents:
                logger.warning(f"Agent {name} not found in DB, skipping")
                continue

            old_prompt = db_agents[name]["system_prompt"]
            agent_id = db_agents[name]["id"]

            if old_prompt == new_prompt:
                logger.info(f"  {name}: prompt unchanged, skipping")
                continue

            old_len = len(old_prompt) if old_prompt else 0
            new_len = len(new_prompt)

            await conn.execute(
                "UPDATE ai_agents SET system_prompt = $1 WHERE id = $2",
                new_prompt, agent_id
            )
            updated += 1
            logger.info(f"  {name}: updated ({old_len} -> {new_len} chars)")

        logger.info(f"\nDone. Updated {updated}/{len(AGENTS)} agents.")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
