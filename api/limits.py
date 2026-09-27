"""In-memory sliding-window rate limits (single API process). Keys are user ids, never client IPs:
behind the Brev proxy every visitor shares one IP."""
import time
from collections import defaultdict, deque

from fastapi import HTTPException

# name -> (max requests, window seconds)
RULES = {
    "analyze_user_min": (10, 60),          # one person checking voice notes by hand never hits this
    "analyze_user_day": (150, 86_400),
    "analyze_global_min": (60, 60),        # caps total GPU/LLM spend even with many throwaway accounts
    "read_user_min": (120, 60),            # history, audio playback, stats, delete
}
_hits: dict[tuple[str, str], deque] = defaultdict(deque)
_last_sweep = 0.0


def _sweep(now: float) -> None:
    """Drop empty buckets so memory does not grow with every user ever seen."""
    global _last_sweep
    if now - _last_sweep < 300:
        return
    _last_sweep = now
    longest = max(w for _, w in RULES.values())
    for key in [k for k, q in _hits.items() if not q or now - q[-1] > longest]:
        del _hits[key]


def hit(rule: str, key: str) -> None:
    """Record one request; raise 429 if the rule is exceeded (the rejected request is not counted)."""
    limit, window = RULES[rule]
    now = time.time()
    _sweep(now)
    q = _hits[(rule, key)]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(429, "too_many_requests", headers={"Retry-After": str(int(window - (now - q[0])) + 1)})
    q.append(now)
