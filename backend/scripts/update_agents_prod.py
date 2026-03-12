"""Full upsert of all 13 AI agents into ai_agents table.

Usage:
    docker exec carbon-backend python -m scripts.update_agents_prod
    cd backend && python -m scripts.update_agents_prod
"""
import asyncio
import json
import os
import sys

import asyncpg

# Ensure backend root is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.seed_ai_agents import AGENTS

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://carbon:CarbonMail2026@localhost:5432/carbon_helpdesk",
)

# Fields to upsert (excluding id, stats, timestamps, coordinator_id)
UPSERT_FIELDS = [
    "name", "human_name", "role", "level", "sector", "specialty",
    "slack_channel", "categories", "tools_enabled", "system_prompt",
    "few_shot_examples", "escalation_keywords", "confidence_threshold",
    "auto_send",
]

# N1 agents -> their N2 coordinator name (same sector)
COORDINATOR_MAP = {
    # Atendimento
    "Isabela-IA": "Juliana-IA",
    "Carol-IA": "Juliana-IA",
    # Logistica
    "Rogerio-IA": "Anderson-IA",
    "Lucas-IA": "Anderson-IA",
    # Garantia
    "Patricia-IA": "Helena-IA",
    "Fernanda-IA": "Helena-IA",
    # Retencao
    "Marina-IA": "Rafael-IA",
    "Beatriz-IA": "Rafael-IA",
    # N2 coordinators -> N3 supervisor
    "Juliana-IA": "Carlos-IA",
    "Anderson-IA": "Carlos-IA",
    "Helena-IA": "Carlos-IA",
    "Rafael-IA": "Carlos-IA",
}


def _val(agent: dict, field: str):
    """Convert Python value to asyncpg-compatible value."""
    v = agent.get(field)
    if field == "few_shot_examples" and v is not None:
        return json.dumps(v)
    return v


async def main():
    conn = await asyncpg.connect(DB_URL)
    print(f"Connected. Upserting {len(AGENTS)} agents...")

    try:
        for ag in AGENTS:
            name = ag["name"]
            # Check if exists
            row = await conn.fetchrow(
                "SELECT id FROM ai_agents WHERE name = $1", name
            )

            if row:
                # UPDATE
                sets = []
                vals = []
                idx = 1
                for f in UPSERT_FIELDS:
                    if f == "name":
                        continue
                    sets.append(f"{f} = ${idx}")
                    vals.append(_val(ag, f))
                    idx += 1
                sets.append(f"updated_at = NOW()")
                sql = f"UPDATE ai_agents SET {', '.join(sets)} WHERE name = ${idx}"
                vals.append(name)
                await conn.execute(sql, *vals)
                print(f"  UPDATED {name} (id={row['id']})")
            else:
                # INSERT
                cols = UPSERT_FIELDS + ["is_active"]
                placeholders = [f"${i+1}" for i in range(len(cols))]
                vals = [_val(ag, f) for f in UPSERT_FIELDS] + [True]
                sql = f"INSERT INTO ai_agents ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
                await conn.execute(sql, *vals)
                print(f"  INSERTED {name}")

        # Set coordinator_id relationships
        print("\nSetting coordinator_id relationships...")
        for agent_name, coord_name in COORDINATOR_MAP.items():
            result = await conn.execute(
                """UPDATE ai_agents
                   SET coordinator_id = (SELECT id FROM ai_agents WHERE name = $1),
                       updated_at = NOW()
                   WHERE name = $2""",
                coord_name,
                agent_name,
            )
            print(f"  {agent_name} -> {coord_name} ({result})")

        # Summary
        count = await conn.fetchval("SELECT COUNT(*) FROM ai_agents")
        print(f"\nDone. Total agents in DB: {count}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
