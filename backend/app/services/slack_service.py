"""Slack integration service for Carbon Expert Hub."""
from __future__ import annotations
import logging
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_slack_client() -> AsyncWebClient | None:
    """Get an async Slack client if configured."""
    if not settings.SLACK_BOT_TOKEN:
        return None
    return AsyncWebClient(token=settings.SLACK_BOT_TOKEN)


async def send_slack_message(channel: str, text: str, thread_ts: str | None = None) -> dict | None:
    """Send a message to a Slack channel, optionally as a thread reply."""
    client = get_slack_client()
    if not client:
        logger.warning("Slack not configured, skipping message send")
        return None

    try:
        kwargs = {"channel": channel, "text": text}
        if thread_ts:
            kwargs["thread_ts"] = thread_ts

        response = await client.chat_postMessage(**kwargs)
        return {"ok": True, "ts": response["ts"], "channel": response["channel"]}
    except SlackApiError as e:
        logger.error(f"Slack API error: {e.response['error']}")
        return None


async def send_ticket_created_notification(channel: str, thread_ts: str, ticket_number: int, subject: str):
    """Send a confirmation that a ticket was created from this Slack message."""
    text = (
        f":ticket: *Ticket #{ticket_number}* criado!\n"
        f"*Assunto:* {subject}\n"
        f"Nossa equipe vai responder em breve."
    )
    return await send_slack_message(channel, text, thread_ts)


async def send_agent_reply_to_slack(channel: str, thread_ts: str, agent_name: str, message_text: str):
    """Send an agent's reply back to the Slack thread."""
    text = f":speech_balloon: *{agent_name}* respondeu:\n\n{message_text}"
    return await send_slack_message(channel, text, thread_ts)


async def get_slack_user_info(user_id: str) -> dict | None:
    """Get Slack user profile info."""
    client = get_slack_client()
    if not client:
        return None

    try:
        response = await client.users_info(user=user_id)
        if response["ok"]:
            user = response["user"]
            profile = user.get("profile", {})
            return {
                "slack_id": user_id,
                "name": profile.get("real_name") or profile.get("display_name") or user.get("name", ""),
                "email": profile.get("email", ""),
            }
    except SlackApiError as e:
        logger.error(f"Slack user info error: {e.response['error']}")
    return None


async def send_agent_transfer(from_agent: str, to_agent: str, ticket_number: int, reason: str, channel: str) -> dict | None:
    """Send inter-agent transfer notification on Slack."""
    text = (
        f":arrows_counterclockwise: *Transferencia de ticket*\n"
        f"*{from_agent}* → *{to_agent}*\n"
        f"Ticket #{ticket_number}: {reason}"
    )
    return await send_slack_message(channel, text)


async def send_agent_escalation(from_agent: str, to_coordinator: str, ticket_number: int, reason: str, channel: str) -> dict | None:
    """Send escalation notification on Slack."""
    text = (
        f":arrow_up: *Escalacao*\n"
        f"*{from_agent}* escalou ticket #{ticket_number} para *{to_coordinator}*\n"
        f"Motivo: {reason}"
    )
    return await send_slack_message(channel, text)


async def send_agent_resolution(agent_name: str, ticket_number: int, channel: str, summary: str = "") -> dict | None:
    """Send resolution notification on Slack."""
    text = (
        f":white_check_mark: *Ticket #{ticket_number} resolvido*\n"
        f"Agente: *{agent_name}*"
    )
    if summary:
        text += f"\nResumo: {summary}"
    return await send_slack_message(channel, text)


async def send_human_pending_request(agent_name: str, ticket_number: int, action: str, assigned_to: str, channel: str) -> dict | None:
    """Request human action via Slack."""
    text = (
        f":hand: *Acao humana necessaria*\n"
        f"Ticket #{ticket_number} — {action}\n"
        f"Solicitado por: *{agent_name}*\n"
        f"Responsavel: @{assigned_to}"
    )
    return await send_slack_message(channel, text)


async def test_slack_connection() -> dict:
    """Test if Slack connection is working."""
    client = get_slack_client()
    if not client:
        return {"ok": False, "error": "SLACK_BOT_TOKEN não configurado"}

    try:
        response = await client.auth_test()
        return {
            "ok": True,
            "bot_name": response.get("user"),
            "team": response.get("team"),
            "bot_id": response.get("user_id"),
        }
    except SlackApiError as e:
        return {"ok": False, "error": str(e.response["error"])}
