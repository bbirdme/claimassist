"""
Simple in-memory rate limiter, per API key. Fine for a single-process mock
demonstrating the gateway boundary; not sufficient for a real multi-instance
deployment (see docs/phase-3-integration-architecture.md).
"""

import time

RATE_LIMIT_PER_MINUTE = 5  # matches the tighter free-tier limits observed
                            # in Phase 0/1 - no point accepting more gateway
                            # traffic than the backend agent can actually serve

_request_log: dict[str, list[float]] = {}


def check_rate_limit(client_key: str) -> bool:
    """Sliding window over the last 60 seconds. Returns True if the request
    is allowed, False if the client has exceeded its limit."""
    now = time.time()
    window_start = now - 60
    history = _request_log.setdefault(client_key, [])

    while history and history[0] < window_start:
        history.pop(0)

    if len(history) >= RATE_LIMIT_PER_MINUTE:
        return False

    history.append(now)
    return True
