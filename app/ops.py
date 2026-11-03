"""Running the demo in public: rate limits, a health check and the scheduled data reset.

All demo data lives in memory (or in temporary files) and is seeded at start-up, so a reset is a restart. The
process exits cleanly after `DEMO_RESET_HOURS` and the container's restart policy brings it back with fresh data.
"""

import asyncio
import os
import signal
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

# Paths that cost nothing to serve and must stay reachable for health checks.
EXEMPT_PREFIXES = ("/static/", "/healthz")


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


class RateLimitMiddleware:
    """Per-client fixed-window limit. Reads and writes have separate budgets; 0 turns a budget off.

    The client is the header named by `DEMO_CLIENT_IP_HEADER` (set it only to a header the host's proxy always
    overwrites, such as `CF-Connecting-IP` on Render), else the first `X-Forwarded-For` entry when
    `DEMO_TRUST_PROXY=1` (set it only behind a proxy that overwrites that header), else the socket peer.
    """

    WINDOW = 60.0
    MAX_CLIENTS = 10_000

    def __init__(self, app, read_limit: int | None = None, write_limit: int | None = None,
                 trust_proxy: bool | None = None, client_header: str | None = None,
                 clock=time.monotonic) -> None:
        self.app = app
        self.read_limit = _int_env("DEMO_RATE_READ", 240) if read_limit is None else read_limit
        self.write_limit = _int_env("DEMO_RATE_WRITE", 60) if write_limit is None else write_limit
        self.trust_proxy = os.environ.get("DEMO_TRUST_PROXY") == "1" if trust_proxy is None else trust_proxy
        header = os.environ.get("DEMO_CLIENT_IP_HEADER", "") if client_header is None else client_header
        self.client_header = header.strip().lower().encode("latin-1")
        self.clock = clock
        self.hits: dict[tuple[str, bool], tuple[float, int]] = {}

    def _client(self, scope) -> str:
        if self.client_header:
            for name, value in scope["headers"]:
                if name == self.client_header:
                    return value.decode("latin-1").strip()
        if self.trust_proxy:
            for name, value in scope["headers"]:
                if name == b"x-forwarded-for":
                    return value.decode("latin-1").split(",")[0].strip()
        client = scope.get("client")
        return client[0] if client else "unknown"

    def _check(self, key: tuple[str, bool], limit: int) -> int:
        """Count a hit; return 0 when allowed, else the seconds until the window resets."""
        now = self.clock()
        if len(self.hits) > self.MAX_CLIENTS:
            self.hits = {k: v for k, v in self.hits.items() if now - v[0] < self.WINDOW}
        start, count = self.hits.get(key, (now, 0))
        if now - start >= self.WINDOW:
            start, count = now, 0
        count += 1
        self.hits[key] = (start, count)
        return 0 if count <= limit else max(1, int(start + self.WINDOW - now) + 1)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"].startswith(EXEMPT_PREFIXES):
            return await self.app(scope, receive, send)
        write = scope["method"] not in ("GET", "HEAD", "OPTIONS")
        limit = self.write_limit if write else self.read_limit
        retry = self._check((self._client(scope), write), limit) if limit > 0 else 0
        if retry:
            body = b'{"detail":"Too many requests. This is a shared demo; please slow down."}'
            await send({"type": "http.response.start", "status": 429, "headers": [
                (b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()),
                (b"retry-after", str(retry).encode())]})
            return await send({"type": "http.response.body", "body": body})
        await self.app(scope, receive, send)


def reset_lifespan(hours: float):
    """A lifespan that stops the process after `hours` so the restart policy reseeds the data. 0 disables it."""

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        task = None
        if hours > 0:
            async def stop_later():
                await asyncio.sleep(hours * 3600)
                os.kill(os.getpid(), signal.SIGTERM)

            task = asyncio.create_task(stop_later())
        yield
        if task:
            task.cancel()

    return lifespan


def reset_hours() -> float:
    try:
        return float(os.environ.get("DEMO_RESET_HOURS", "0"))
    except ValueError:
        return 0.0
