from __future__ import annotations

import secrets

import redis
from django.conf import settings


TICKET_PREFIX = "chat:ws:ticket:"


def _ticket_ttl_seconds() -> int:
    return int(getattr(settings, "CHAT_WS_TICKET_TTL_SECONDS", 60))


def _redis_client():
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def issue_ticket(*, user_id, session_id) -> str:
    ticket = secrets.token_urlsafe(32)
    payload = f"{user_id}:{session_id}"
    client = _redis_client()
    client.setex(f"{TICKET_PREFIX}{ticket}", _ticket_ttl_seconds(), payload)
    return ticket


def consume_ticket(ticket: str) -> tuple[str, str] | None:
    if not ticket:
        return None

    key = f"{TICKET_PREFIX}{ticket}"
    client = _redis_client()
    with client.pipeline() as pipe:
        pipe.get(key)
        pipe.delete(key)
        value, _deleted = pipe.execute()

    if not value:
        return None

    user_id, session_id = value.split(":", 1)
    return user_id, session_id
