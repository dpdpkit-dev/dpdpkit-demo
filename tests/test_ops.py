import asyncio
import importlib.util
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import ops
from app.main import app
from app.packages import PACKAGES


def limited(**kwargs):
    inner = FastAPI()

    @inner.get("/x")
    def read():
        return {}

    @inner.post("/x")
    def write():
        return {}

    @inner.get("/healthz")
    def health():
        return {}

    inner.add_middleware(ops.RateLimitMiddleware, **kwargs)
    return TestClient(inner)


def test_reads_are_limited_with_retry_after():
    c = limited(read_limit=3, write_limit=0)
    assert [c.get("/x").status_code for _ in range(4)] == [200, 200, 200, 429]
    r = c.get("/x")
    assert int(r.headers["retry-after"]) >= 1
    assert "slow down" in r.json()["detail"]


def test_writes_have_their_own_budget():
    c = limited(read_limit=100, write_limit=1)
    assert c.post("/x").status_code == 200
    assert c.post("/x").status_code == 429
    assert c.get("/x").status_code == 200


def test_window_resets():
    now = [0.0]
    c = limited(read_limit=1, write_limit=0, clock=lambda: now[0])
    assert c.get("/x").status_code == 200
    assert c.get("/x").status_code == 429
    now[0] = 61
    assert c.get("/x").status_code == 200


def test_health_is_exempt():
    c = limited(read_limit=1, write_limit=1)
    assert all(c.get("/healthz").status_code == 200 for _ in range(5))


def test_forwarded_for_only_trusted_behind_proxy():
    headers = lambda ip: {"X-Forwarded-For": ip}  # noqa: E731
    trusted = limited(read_limit=1, write_limit=0, trust_proxy=True)
    assert trusted.get("/x", headers=headers("1.1.1.1")).status_code == 200
    assert trusted.get("/x", headers=headers("2.2.2.2")).status_code == 200
    assert trusted.get("/x", headers=headers("1.1.1.1")).status_code == 429
    direct = limited(read_limit=1, write_limit=0, trust_proxy=False)
    assert direct.get("/x", headers=headers("1.1.1.1")).status_code == 200
    assert direct.get("/x", headers=headers("2.2.2.2")).status_code == 429


def test_client_ip_header_is_used_and_cannot_be_forged_with_forwarded_for():
    client = limited(read_limit=1, write_limit=0, client_header="CF-Connecting-IP")
    first = {"CF-Connecting-IP": "203.0.113.1", "X-Forwarded-For": "198.51.100.1"}
    assert client.get("/x", headers=first).status_code == 200
    forged = {"CF-Connecting-IP": "203.0.113.1", "X-Forwarded-For": "198.51.100.2"}
    assert client.get("/x", headers=forged).status_code == 429
    other = {"CF-Connecting-IP": "203.0.113.2"}
    assert client.get("/x", headers=other).status_code == 200


def test_healthz():
    assert TestClient(app).get("/healthz").json() == {"status": "ok"}


def test_reset_lifespan_terminates_after_interval(monkeypatch):
    killed = []
    monkeypatch.setattr(ops.os, "kill", lambda pid, sig: killed.append(sig))
    real_sleep = asyncio.sleep

    async def fast_sleep(seconds):
        assert seconds == 3600
        await real_sleep(0)

    monkeypatch.setattr(ops.asyncio, "sleep", fast_sleep)

    async def run():
        async with ops.reset_lifespan(1)(FastAPI()):
            await real_sleep(0.05)

    asyncio.run(run())
    assert killed == [ops.signal.SIGTERM]


def test_reset_disabled_by_default(monkeypatch):
    monkeypatch.delenv("DEMO_RESET_HOURS", raising=False)
    assert ops.reset_hours() == 0


def test_smoke_script_covers_every_page():
    path = Path(__file__).parent.parent / "scripts" / "smoke.py"
    spec = importlib.util.spec_from_file_location("smoke", path)
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    assert smoke.SLUGS == [p.slug for p in PACKAGES]
