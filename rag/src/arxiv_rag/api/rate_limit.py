"""Simple in-memory token-bucket rate limiter — no external dependencies."""
import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request

# 10 requests per 60 seconds per IP on expensive endpoints
_RATE = 10
_PERIOD = 60.0

_lock = threading.Lock()
_buckets: dict[str, dict] = defaultdict(
    lambda: {"tokens": float(_RATE), "last": time.monotonic()}
)


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    return xff.split(",")[0].strip() if xff else (request.client.host if request.client else "unknown")


def check_rate_limit(request: Request) -> None:
    """FastAPI dependency. Raises 429 if the caller exceeds the rate limit."""
    ip = _client_ip(request)
    now = time.monotonic()
    with _lock:
        bucket = _buckets[ip]
        elapsed = now - bucket["last"]
        bucket["tokens"] = min(_RATE, bucket["tokens"] + elapsed * (_RATE / _PERIOD))
        bucket["last"] = now
        if bucket["tokens"] < 1:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded — please wait before sending another request.",
                headers={"Retry-After": str(int(_PERIOD))},
            )
        bucket["tokens"] -= 1
