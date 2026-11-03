"""The live demo for the any-stack page: dpdpkit-server plus @dpdpkit/embed on a plain HTML page.

The server's ASGI app runs in this process, mounted at /demo/server/api, with a throwaway SQLite database. The
page itself (page.html) is plain HTML that loads @dpdpkit/embed with a script tag. The routes under
/demo/server/backend stand in for the customer's own backend, which could be Node, PHP or Java: it holds the
API key, knows who is signed in (a cookie naming a fictional user) and asks the server for a short-lived token.
"""

import atexit
import shutil
import tempfile
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from dpdpkit.server.app import create_app
from dpdpkit.server.auth import generate_api_key
from dpdpkit.server.settings import Settings

from ..fastapi_demo import DEMO_USERS
from ..packages import DISCLAIMER, FICTIONAL_NOTE

PREFIX = "/demo/server"
API_PREFIX = f"{PREFIX}/api"
COOKIE = "demo_user"
PAGE = Path(__file__).with_name("page.html")


def install(app: FastAPI) -> None:
    db_dir = tempfile.mkdtemp(prefix="dpdpkit-server-demo-")
    atexit.register(shutil.rmtree, db_dir, ignore_errors=True)
    api_key, api_key_hash = generate_api_key()  # new on every start; only the backend below knows it
    settings = Settings(
        database_url=f"sqlite:///{Path(db_dir, 'demo.db').as_posix()}",
        signing_key="demo-only-signing-key",
        api_key_hashes=(api_key_hash,),
        config_path=Path(__file__).parent.parent / "dpdpkit.yaml",
        migrate_on_startup=True,
    )
    server = create_app(settings)

    def signed_in(request: Request) -> str | None:
        user = request.cookies.get(COOKIE)
        return user if user in DEMO_USERS else None

    @app.get(f"{PREFIX}/", response_class=HTMLResponse)
    def page(request: Request) -> str:
        user = signed_in(request)
        who = (
            f"You are acting as {DEMO_USERS[user]['name']}."
            if user
            else "You are not signed in, so the widgets cannot act yet."
        )
        links = " ".join(f'<a href="{PREFIX}/backend/act-as/{id}">{u["name"]}</a>' for id, u in DEMO_USERS.items())
        return (
            PAGE.read_text(encoding="utf-8")
            .replace("{{ who }}", who)
            .replace("{{ act_as }}", links)
            .replace("{{ prefix }}", PREFIX)
            .replace("{{ api }}", f"{API_PREFIX}/dpdp")
            .replace("{{ disclaimer }}", DISCLAIMER)
            .replace("{{ fictional_note }}", FICTIONAL_NOTE)
        )

    @app.get(f"{PREFIX}/backend/act-as/{{user}}")
    def act_as(user: str) -> RedirectResponse:
        if user not in DEMO_USERS:
            raise HTTPException(404)
        response = RedirectResponse(f"{PREFIX}/", status_code=302)
        response.set_cookie(COOKIE, user, samesite="lax")
        return response

    @app.post(f"{PREFIX}/backend/privacy-token")
    async def privacy_token(request: Request) -> JSONResponse:
        """What the customer's backend does: check who is signed in, then ask dpdpkit-server for a token."""
        user = signed_in(request)
        if user is None:
            return JSONResponse({"detail": "not signed in"}, status_code=401)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server), base_url="http://server") as http:
            issued = await http.post("/v1/tokens", json={"subject": user}, headers={"Authorization": f"Bearer {api_key}"})
        issued.raise_for_status()
        return JSONResponse(issued.json())

    app.mount(API_PREFIX, server)
