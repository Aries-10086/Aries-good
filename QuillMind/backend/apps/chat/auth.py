from __future__ import annotations

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def _get_user(user_id):
    User = get_user_model()
    try:
        return User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        return AnonymousUser()


class JWTQueryAuthMiddleware:
    """Authenticate WebSockets using an access token in `?token=`."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        close_old_connections()
        query = parse_qs(scope.get("query_string", b"").decode("utf-8"))
        token_value = query.get("token", [""])[0]
        user = AnonymousUser()

        if token_value:
            try:
                token = AccessToken(token_value)
                user = await _get_user(token["user_id"])
            except (InvalidToken, TokenError, KeyError, ValueError):
                pass

        return await self.app({**scope, "user": user}, receive, send)
