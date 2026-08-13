from __future__ import annotations

from typing import Optional

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


def _user_ident(user) -> Optional[str]:
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    ident = getattr(user, "pk", None) or getattr(user, "id", None)
    return str(ident) if ident is not None else None


class SafeUserRateThrottle(UserRateThrottle):
    def get_cache_key(self, request, view):
        ident = _user_ident(request.user)
        if ident is None:
            return None
        return self.cache_format % {"scope": self.scope, "ident": ident}


class AuthRateThrottle(AnonRateThrottle):
    scope = "auth"


class GenerationRateThrottle(SafeUserRateThrottle):
    scope = "generation"


class DocumentReviewRateThrottle(SafeUserRateThrottle):
    scope = "document_review"
