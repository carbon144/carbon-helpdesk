from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chatbot_flow import ChatbotFlow


# In-memory flow state storage (could be replaced with Redis)
_flow_states: dict[str, dict] = {}


class ChatbotEngine:
    """Engine that processes messages against chatbot flows."""

    async def process_message(
        self,
        db: AsyncSession,
        conversation: object,
        message_text: str,
        visitor_id: Optional[str] = None,
    ) -> Optional[dict]:
        """Check active ChatbotFlows for matching trigger and execute flow.
        Returns action result dict or None if no flow matched."""
        flow = await self.match_flow(db, message_text)
        if not flow:
            return None

        context = {
            "conversation": conversation,
            "message_text": message_text,
            "visitor_id": visitor_id,
            "flow_id": flow.id,
            "responses": [],
        }

        # Track state for multi-step flows
        state_key = visitor_id or (getattr(conversation, "id", None) or "unknown")
        _flow_states[state_key] = {"flow_id": flow.id, "step_index": 0}

        steps = flow.steps or []
        for step in steps:
            result = self.execute_step(step, context)
            context["responses"].append(result)
            if result.get("type") == "transfer_to_agent":
                break  # stop after transfer
            if result.get("type") == "wait_response":
                break  # pause and wait for next message

        return {
            "flow_id": flow.id,
            "flow_name": flow.name,
            "responses": context["responses"],
            "matched": True,
        }

    async def match_flow(
        self,
        db: AsyncSession,
        message_text: str,
        trigger_type: Optional[str] = None,
    ) -> Optional[ChatbotFlow]:
        """Find matching active flow by keyword/trigger."""
        query = select(ChatbotFlow).where(ChatbotFlow.active.is_(True))
        if trigger_type:
            query = query.where(ChatbotFlow.trigger_type == trigger_type)

        result = await db.execute(query)
        flows = list(result.scalars().all())

        text_lower = message_text.lower().strip()

        for flow in flows:
            if flow.trigger_type == "keyword":
                keywords = (flow.trigger_config or {}).get("keywords", [])
                for kw in keywords:
                    if kw.lower() in text_lower:
                        return flow
            elif flow.trigger_type == "exact":
                exact = (flow.trigger_config or {}).get("text", "")
                if exact.lower() == text_lower:
                    return flow
            elif flow.trigger_type == "greeting":
                greetings = ["oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "hello", "hi"]
                if text_lower in greetings:
                    return flow
            elif flow.trigger_type == "any":
                return flow

        return None

    def execute_step(self, step: dict, context: dict) -> dict:
        """Execute a single flow step and return result."""
        step_type = step.get("type", "send_message")

        if step_type == "send_message":
            return {
                "type": "send_message",
                "content": step.get("content", ""),
            }
        elif step_type == "wait_response":
            return {
                "type": "wait_response",
                "prompt": step.get("prompt", ""),
            }
        elif step_type == "lookup_order":
            return {
                "type": "lookup_order",
                "order_field": step.get("order_field", "order_number"),
                "message": step.get("message", "Buscando informacoes do pedido..."),
            }
        elif step_type == "suggest_article":
            return {
                "type": "suggest_article",
                "query": context.get("message_text", ""),
                "message": step.get("message", "Encontrei estes artigos que podem ajudar:"),
            }
        elif step_type == "transfer_to_agent":
            return {
                "type": "transfer_to_agent",
                "message": step.get("message", "Transferindo para um atendente..."),
            }
        else:
            return {
                "type": "unknown",
                "step": step,
            }


# CRUD helpers for flows

async def list_flows(db: AsyncSession) -> list[ChatbotFlow]:
    result = await db.execute(
        select(ChatbotFlow).order_by(ChatbotFlow.created_at.desc())
    )
    return list(result.scalars().all())


async def get_flow(db: AsyncSession, flow_id: str) -> Optional[ChatbotFlow]:
    result = await db.execute(
        select(ChatbotFlow).where(ChatbotFlow.id == flow_id)
    )
    return result.scalar_one_or_none()


async def create_flow(db: AsyncSession, data: dict) -> ChatbotFlow:
    flow = ChatbotFlow(**data)
    db.add(flow)
    await db.commit()
    await db.refresh(flow)
    return flow


async def update_flow(
    db: AsyncSession, flow_id: str, data: dict
) -> Optional[ChatbotFlow]:
    flow = await get_flow(db, flow_id)
    if not flow:
        return None
    for key, value in data.items():
        setattr(flow, key, value)
    await db.commit()
    await db.refresh(flow)
    return flow


async def delete_flow(db: AsyncSession, flow_id: str) -> bool:
    flow = await get_flow(db, flow_id)
    if not flow:
        return False
    await db.delete(flow)
    await db.commit()
    return True
