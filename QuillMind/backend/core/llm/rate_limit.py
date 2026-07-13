from __future__ import annotations

import logging
from typing import Any

import redis
from django.conf import settings

from .exceptions import LLMRateLimitError


logger = logging.getLogger(__name__)


class RedisRateLimiter:
    def __init__(
        self,
        redis_url: str | None = None,
        *,
        limit: int | None = None,
        window_seconds: int = 60,
        key_prefix: str = "llm:rate",
    ):
        self.redis_url = redis_url or settings.REDIS_URL
        self.limit = limit or settings.LLM_RATE_LIMIT_PER_MINUTE
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix
        self._client: Any | None = None

    @property
    def client(self):
        if self._client is None:
            self._client = redis.Redis.from_url(self.redis_url, decode_responses=True)

        return self._client

    def check(self, user_id: str | int | None):
        if not user_id or self.limit <= 0:
            return

        key = f"{self.key_prefix}:{user_id}"

        try:
            count = int(self.client.incr(key))
            if count == 1:
                self.client.expire(key, self.window_seconds)
        except redis.RedisError:
            logger.warning("LLM rate limiter unavailable; allowing request.", exc_info=True)
            return

        if count > self.limit:
            raise LLMRateLimitError("LLM rate limit exceeded for this user.")
