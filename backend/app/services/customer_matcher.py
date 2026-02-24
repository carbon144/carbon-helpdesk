"""Customer matching service.

Finds existing customers in the database based on extracted data (CPF, email, phone)
and locates open tickets for merge suggestions.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.ticket import Ticket

logger = logging.getLogger(__name__)


async def _follow_merge_chain(db: AsyncSession, customer: Customer, max_depth: int = 10) -> Customer:
    """Follow merged_into_id chain to find the actual current customer.

    If a customer was merged into another, we follow the chain until we find
    the final (non-merged) customer. max_depth prevents infinite loops.
    """
    visited = {customer.id}
    current = customer

    for _ in range(max_depth):
        merged_into_id = getattr(current, "merged_into_id", None)
        if not merged_into_id:
            return current

        if merged_into_id in visited:
            logger.warning(
                "Circular merge chain detected for customer %s", current.id
            )
            return current

        visited.add(merged_into_id)
        result = await db.execute(
            select(Customer).where(Customer.id == merged_into_id)
        )
        next_customer = result.scalar_one_or_none()

        if next_customer is None:
            logger.warning(
                "Broken merge chain: customer %s points to non-existent %s",
                current.id,
                merged_into_id,
            )
            return current

        current = next_customer

    logger.warning("Merge chain exceeded max depth (%d) for customer %s", max_depth, customer.id)
    return current


async def _match_by_cpf(db: AsyncSession, cpf: str) -> Customer | None:
    """Exact match on Customer.cpf."""
    result = await db.execute(
        select(Customer).where(Customer.cpf == cpf)
    )
    return result.scalar_one_or_none()


async def _match_by_email(db: AsyncSession, email: str) -> Customer | None:
    """Exact match on Customer.email or in Customer.alternate_emails (if field exists)."""
    # Primary email match
    result = await db.execute(
        select(Customer).where(func.lower(Customer.email) == email.lower())
    )
    customer = result.scalar_one_or_none()
    if customer:
        return customer

    # Try alternate_emails (ARRAY field) — may not exist yet in the model
    if hasattr(Customer, "alternate_emails"):
        try:
            result = await db.execute(
                select(Customer).where(
                    Customer.alternate_emails.any(email.lower())
                )
            )
            customer = result.scalar_one_or_none()
            if customer:
                return customer
        except Exception:
            # Column may not exist in DB yet even if defined in model
            logger.debug("alternate_emails query failed — column may not exist yet")

    return None


async def _match_by_phone(db: AsyncSession, phone: str) -> Customer | None:
    """Exact match on Customer.phone."""
    result = await db.execute(
        select(Customer).where(Customer.phone == phone)
    )
    return result.scalar_one_or_none()


async def find_matching_customer(
    db: AsyncSession,
    cpf: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    shopify_order_id: Optional[str] = None,
) -> Customer | None:
    """Find an existing customer matching the provided identifiers.

    Matching priority (highest to lowest confidence):
      1. CPF — exact match
      2. Email — exact match on primary or alternate emails
      3. Phone — exact match

    If the matched customer has been merged into another, follows the chain
    to return the current (non-merged) customer record.

    Args:
        db: Async database session.
        cpf: Customer CPF (Brazilian tax ID).
        phone: Customer phone number.
        email: Customer email address.
        shopify_order_id: Shopify order ID (reserved for future use).

    Returns:
        The matched Customer or None if no match is found.
    """
    matchers: list[tuple[str, str, callable]] = []

    if cpf and cpf.strip():
        matchers.append(("cpf", cpf.strip(), _match_by_cpf))
    if email and email.strip():
        matchers.append(("email", email.strip(), _match_by_email))
    if phone and phone.strip():
        matchers.append(("phone", phone.strip(), _match_by_phone))

    for field_name, value, matcher_fn in matchers:
        customer = await matcher_fn(db, value)
        if customer:
            logger.info(
                "Customer matched by %s=%s -> customer_id=%s",
                field_name,
                value,
                customer.id,
            )
            # Follow merge chain if applicable
            customer = await _follow_merge_chain(db, customer)
            return customer

    return None


async def find_matching_ticket(
    db: AsyncSession,
    customer_id: str,
    status_not_in: Optional[list[str]] = None,
) -> Ticket | None:
    """Find the most recent open ticket for a customer.

    Useful for suggesting ticket merges when a customer contacts support
    about an already-open issue.

    Args:
        db: Async database session.
        customer_id: The customer UUID to search tickets for.
        status_not_in: Statuses to exclude. Defaults to
            ["closed", "resolved", "archived", "merged"].

    Returns:
        The most recent non-excluded Ticket, or None.
    """
    if status_not_in is None:
        status_not_in = ["closed", "resolved", "archived", "merged"]

    result = await db.execute(
        select(Ticket)
        .where(
            Ticket.customer_id == customer_id,
            Ticket.status.notin_(status_not_in),
        )
        .order_by(desc(Ticket.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()
