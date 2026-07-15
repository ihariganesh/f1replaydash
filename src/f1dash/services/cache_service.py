import json
from datetime import datetime, timedelta
from typing import Any


class CacheService:
    """Simple cache abstraction with optional Redis backend and in-process fallback."""

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis = None
        self._memory: dict[str, tuple[datetime, Any]] = {}

        if redis_url:
            try:
                import redis  # pylint: disable=import-outside-toplevel

                self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
                self._redis.ping()
            except Exception:  # noqa: BLE001
                self._redis = None

    def get_json(self, key: str) -> Any | None:
        if self._redis:
            raw = self._redis.get(key)
            if raw:
                return json.loads(raw)
            return None

        item = self._memory.get(key)
        if not item:
            return None

        expires_at, payload = item
        if datetime.utcnow() >= expires_at:
            self._memory.pop(key, None)
            return None
        return payload

    def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        if self._redis:
            self._redis.setex(key, ttl_seconds, json.dumps(value, default=str))
            return

        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        self._memory[key] = (expires_at, value)
