from __future__ import annotations

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections


@database_sync_to_async
def _get_user(user_id):
    User = get_user_model()
    try:
        return User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        return AnonymousUser()


@database_sync_to_async
def _consume_ticket(ticket: str):
    from .ws_tickets import consume_ticket

    return consume_ticket(ticket)


class WebSocketTicketAuthMiddleware:
    """Authenticate WebSockets using a one-time ticket from REST `ws-ticket`."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        close_old_connections()
        query = parse_qs(scope.get("query_string", b"").decode("utf-8"))
        ticket_value = query.get("ticket", [""])[0]
        user = AnonymousUser()

        if ticket_value:
            payload = await _consume_ticket(ticket_value)
            if payload is not None:
                user_id, _session_id = payload
                user = await _get_user(user_id)

        return await self.app({**scope, "user": user}, receive, send)
