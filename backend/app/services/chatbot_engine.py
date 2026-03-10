"""Chatbot engine with multi-step flow state tracking."""

import logging
import re
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chatbot_flow import ChatbotFlow

logger = logging.getLogger(__name__)


class ChatbotEngine:
    """Engine that processes messages against chatbot flows with multi-step state."""

    async def process_message(
        self,
        db: AsyncSession,
        conversation: object,
        message_text: str,
        visitor_id: Optional[str] = None,
    ) -> Optional[dict]:
        """Check for active flow state first (resume), otherwise match new flow.
        Returns action result dict or None if no flow matched."""

        text_lower = message_text.lower().strip()

        # Allow user to reset to main menu anytime
        if text_lower in ("menu", "voltar", "voltar ao menu", "voltar menu", "inicio", "início", "0", "encerrar"):
            self._clear_state(conversation)
            flow = await self.match_flow(db, "oi", trigger_type="greeting")
            if flow:
                return await self._execute_flow(db, conversation, flow, message_text, visitor_id)

        # Check if there's an active flow state to resume
        state = self._get_state(conversation)
        if state:
            return await self._resume_flow(db, conversation, message_text, state)

        # Check if this is a menu option selection (by number, id, or label)
        meta = getattr(conversation, "metadata_", None) or {}
        menu_target = self._resolve_menu_selection(text_lower, meta)
        if menu_target:
            flow = await self.match_flow(db, menu_target)
            if flow:
                return await self._execute_flow(db, conversation, flow, menu_target, visitor_id)

        # No active state — try to match a new flow
        flow = await self.match_flow(db, message_text)
        if not flow:
            return None

        return await self._execute_flow(db, conversation, flow, message_text, visitor_id)

    def _resolve_menu_selection(self, text_lower: str, meta: dict) -> Optional[str]:
        """Check if text matches a menu option and return the option id for flow matching.
        Supports: exact match, number, partial match, sim/não prefix match."""
        last_menu = meta.get("last_menu_options")
        if not last_menu:
            return None
        # Normalize: "opcao 1", "opção 1", "opção1" → "1"
        num_match = re.match(r"^op[cç][aã]o\s*(\d+)$", text_lower)
        if num_match:
            text_lower = num_match.group(1)

        # Pass 1: exact match on id, label, or number
        for i, opt in enumerate(last_menu):
            opt_id = (opt.get("id") or "").lower()
            opt_label = (opt.get("label") or "").lower()
            if text_lower == opt_id or text_lower == opt_label or text_lower == str(i + 1):
                return opt_id

        # Pass 2: partial match — user text contained in label or label contained in user text
        for opt in last_menu:
            opt_id = (opt.get("id") or "").lower()
            opt_label = (opt.get("label") or "").lower()
            opt_desc = (opt.get("description") or "").lower()
            if not opt_label:
                continue
            if text_lower in opt_label or opt_label in text_lower:
                return opt_id
            if opt_desc and (text_lower in opt_desc or opt_desc in text_lower):
                return opt_id

        # Pass 3: sim/não prefix match — "sim" matches first option starting with "sim", etc.
        text_clean = re.sub(r"[,\.!?\s]+", " ", text_lower).strip()
        first_word = text_clean.split()[0] if text_clean else ""
        if first_word in ("sim", "s", "yes"):
            for opt in last_menu:
                opt_label = (opt.get("label") or "").lower()
                if opt_label.startswith("sim"):
                    return (opt.get("id") or "").lower()
        elif first_word in ("não", "nao", "n", "no"):
            for opt in last_menu:
                opt_label = (opt.get("label") or "").lower()
                if opt_label.startswith("não") or opt_label.startswith("nao"):
                    return (opt.get("id") or "").lower()

        return None

    async def match_flow(
        self,
        db: AsyncSession,
        message_text: str,
        trigger_type: Optional[str] = None,
    ) -> Optional[ChatbotFlow]:
        """Find matching active flow by trigger type with priority: exact > keyword > greeting > any."""
        query = select(ChatbotFlow).where(ChatbotFlow.active.is_(True))
        if trigger_type:
            query = query.where(ChatbotFlow.trigger_type == trigger_type)

        result = await db.execute(query)
        flows = list(result.scalars().all())

        text_lower = message_text.lower().strip()

        # Group by priority
        exact_matches = []
        keyword_matches = []
        greeting_matches = []
        any_matches = []

        for flow in flows:
            if flow.trigger_type == "exact":
                exact_text = (flow.trigger_config or {}).get("text", "")
                if exact_text.lower() == text_lower:
                    exact_matches.append(flow)
            elif flow.trigger_type == "keyword":
                keywords = (flow.trigger_config or {}).get("keywords", [])
                best_kw_len = 0
                for kw in keywords:
                    if kw.lower() in text_lower:
                        best_kw_len = max(best_kw_len, len(kw))
                if best_kw_len > 0:
                    keyword_matches.append((best_kw_len, flow))
            elif flow.trigger_type == "greeting":
                greetings = [
                    "oi", "ola", "olá", "bom dia", "boa tarde", "boa noite",
                    "hello", "hi", "hey", "oii", "oie", "opa", "eai", "e ai",
                    "bom dua", "boa tde", "boa trd", "boa noit", "bon dia",
                    "bom diaaa", "boa tardeee", "boa noiteee",
                    "ola boa tarde", "oi boa tarde", "oi bom dia", "oi boa noite",
                    "olá boa tarde", "olá bom dia", "olá boa noite",
                ]
                # Match exact or first line of multiline message
                first_line = text_lower.split("\n")[0].strip()
                if text_lower in greetings or first_line in greetings:
                    greeting_matches.append(flow)
            elif flow.trigger_type == "any":
                any_matches.append(flow)

        # Sort keyword matches by longest keyword (most specific first)
        keyword_matches.sort(key=lambda x: x[0], reverse=True)
        keyword_flows = [flow for _, flow in keyword_matches]

        # Return first match in priority order
        for group in (exact_matches, keyword_flows, greeting_matches, any_matches):
            if group:
                return group[0]

        return None

    async def _execute_flow(
        self,
        db: AsyncSession,
        conversation: object,
        flow: ChatbotFlow,
        message_text: str,
        visitor_id: Optional[str] = None,
    ) -> dict:
        """Execute a flow from the beginning, stopping at wait points."""
        steps = flow.steps or []
        responses: list[dict] = []
        collected_data: dict = {}

        for i, step in enumerate(steps):
            result = self._process_step(step, collected_data, message_text, conversation)
            responses.append(result)

            step_type = result.get("type")

            if step_type == "transfer_to_agent":
                self._clear_state(conversation)
                break

            if step_type in ("wait_response", "collect_input"):
                # Save state and pause — next message will resume
                self._save_state(conversation, {
                    "flow_id": str(flow.id),
                    "step_index": i + 1,
                    "collected_data": collected_data,
                    "expecting_field": result.get("field"),
                })
                break

            if step_type == "condition":
                # Condition steps don't produce visible output; just continue
                continue

        return {
            "flow_id": str(flow.id),
            "flow_name": flow.name,
            "responses": responses,
            "matched": True,
        }

    async def _resume_flow(
        self,
        db: AsyncSession,
        conversation: object,
        message_text: str,
        state: dict,
    ) -> Optional[dict]:
        """Resume a flow from saved state, storing user input."""
        flow_id = state.get("flow_id")
        step_index = state.get("step_index", 0)
        collected_data = state.get("collected_data", {})
        expecting_field = state.get("expecting_field")

        # Load flow from DB
        result = await db.execute(
            select(ChatbotFlow).where(ChatbotFlow.id == flow_id)
        )
        flow = result.scalar_one_or_none()
        if not flow:
            self._clear_state(conversation)
            return None

        # Store user input in the expected field
        if expecting_field:
            collected_data[expecting_field] = message_text.strip()

        steps = flow.steps or []
        responses: list[dict] = []

        for i in range(step_index, len(steps)):
            step = steps[i]
            r = self._process_step(step, collected_data, message_text, conversation)
            responses.append(r)

            step_type = r.get("type")

            if step_type == "transfer_to_agent":
                self._clear_state(conversation)
                break

            if step_type in ("wait_response", "collect_input"):
                self._save_state(conversation, {
                    "flow_id": str(flow.id),
                    "step_index": i + 1,
                    "collected_data": collected_data,
                    "expecting_field": r.get("field"),
                })
                break

            if step_type == "condition":
                continue
        else:
            # Reached end of flow
            self._clear_state(conversation)

        return {
            "flow_id": str(flow.id),
            "flow_name": flow.name,
            "responses": responses,
            "matched": True,
        }

    def _process_step(self, step: dict, collected_data: dict, message_text: str, conversation: object = None) -> dict:
        """Execute a single flow step and return result."""
        step_type = step.get("type", "send_message")

        if step_type == "send_message":
            content = self._substitute_vars(step.get("content") or step.get("message") or "", collected_data)
            return {"type": "send_message", "content": content}

        elif step_type == "send_menu":
            content = self._substitute_vars(step.get("content") or step.get("message") or "", collected_data)
            options = step.get("options", [])
            # Save menu options in metadata for selection routing
            if conversation and hasattr(conversation, "metadata_"):
                meta = dict(getattr(conversation, "metadata_", None) or {})
                meta["last_menu_options"] = options
                conversation.metadata_ = meta
                flag_modified(conversation, "metadata_")
            return {
                "type": "send_menu",
                "content": content,
                "options": options,
            }

        elif step_type == "collect_input":
            prompt = self._substitute_vars(step.get("prompt") or step.get("message") or "", collected_data)
            field = step.get("field") or step.get("variable") or "input"
            result = {
                "type": "collect_input",
                "content": prompt,
                "field": field,
            }
            if step.get("options"):
                result["options"] = step["options"]
            return result

        elif step_type == "wait_response":
            prompt = self._substitute_vars(step.get("prompt", ""), collected_data)
            return {"type": "wait_response", "prompt": prompt}

        elif step_type == "lookup_order":
            return {
                "type": "lookup_order",
                "order_field": step.get("order_field", "order_number"),
                "collected_data": collected_data,
                "message": step.get("message", "Buscando informações do pedido..."),
            }

        elif step_type == "lookup_troque":
            return {
                "type": "lookup_troque",
                "variable": step.get("variable", "order_number"),
                "collected_data": collected_data,
                "found_message": step.get("found_message", ""),
                "not_found_message": step.get("not_found_message", ""),
            }

        elif step_type == "lookup_invoice":
            return {
                "type": "lookup_invoice",
                "variable": step.get("variable", "order_number"),
                "collected_data": collected_data,
                "found_message": step.get("found_message", ""),
                "not_found_message": step.get("not_found_message", ""),
            }

        elif step_type == "suggest_article":
            return {
                "type": "suggest_article",
                "query": message_text,
                "message": step.get("message", "Encontrei estes artigos que podem ajudar:"),
            }

        elif step_type == "transfer_to_agent":
            message = self._substitute_vars(
                step.get("message", "Transferindo para um atendente..."), collected_data,
            )
            return {
                "type": "transfer_to_agent",
                "message": message,
                "collected_data": collected_data,
            }

        elif step_type == "transfer_to_ai":
            return {"type": "transfer_to_ai"}

        elif step_type == "condition":
            # Evaluate condition — for now just pass through
            return {"type": "condition", "step": step}

        else:
            return {"type": "unknown", "step": step}

    def _substitute_vars(self, text: str, collected_data: dict) -> str:
        """Replace {{field_name}} placeholders with collected_data values."""
        if not text or not collected_data:
            return text

        def replacer(match):
            key = match.group(1).strip()
            return collected_data.get(key, match.group(0))

        return re.sub(r"\{\{(\w+)\}\}", replacer, text)

    # ── State helpers ──

    def _get_state(self, conversation: object) -> Optional[dict]:
        """Read chatbot_state from conversation.metadata_."""
        meta = getattr(conversation, "metadata_", None) or {}
        return meta.get("chatbot_state")

    def _save_state(self, conversation: object, state: dict):
        """Save chatbot_state into conversation.metadata_."""
        meta = dict(getattr(conversation, "metadata_", None) or {})
        meta["chatbot_state"] = state
        conversation.metadata_ = meta
        flag_modified(conversation, "metadata_")

    def _clear_state(self, conversation: object):
        """Remove chatbot_state from conversation.metadata_."""
        meta = dict(getattr(conversation, "metadata_", None) or {})
        meta.pop("chatbot_state", None)
        conversation.metadata_ = meta
        flag_modified(conversation, "metadata_")


# ── CRUD helpers for flows (unchanged) ──

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
