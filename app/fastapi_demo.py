"""The live demo for the FastAPI page: dpdpkit-fastapi mounted on this site at /demo/fastapi/dpdp.

The backend is the published dpdpkit-fastapi package with an in-memory SQLite database, so the data
resets whenever the site restarts. The "login" is a stand-in: the page sends the chosen fictional user
in the X-User header, and @dpdpkit/react runs the consent, preferences and rights request flows against it.
"""

from pathlib import Path

from fastapi import Depends, FastAPI, Request
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from dpdpkit import ConsoleNotifier, Contact
from dpdpkit.fastapi import DPDPKit, require_consent

PREFIX = "/demo/fastapi/dpdp"

# Fictional people the visitor can act as.
DEMO_USERS = {
    "u_asha": {"name": "Asha Rao", "email": "asha@example.in", "phone": "+919800000042"},
    "u_vikram": {"name": "Vikram Shah", "email": "vikram@example.in", "phone": "+919800000043"},
}


def current_user(request: Request) -> str | None:
    user = request.headers.get("X-User")
    return user if user in DEMO_USERS else None


def contact_for(principal: str) -> Contact | None:
    user = DEMO_USERS.get(principal)
    return Contact(email=user["email"], phone=user["phone"]) if user else None


def install(app: FastAPI) -> DPDPKit:
    dpdp = DPDPKit(
        engine=create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool),
        config=Path(__file__).parent / "dpdpkit.yaml",
        principal_resolver=current_user,
        notifier=ConsoleNotifier(),
        contact_resolver=contact_for,
        signing_key="demo-only-signing-key",
        migrate_on_startup=True,
    )
    dpdp.install(app, prefix=PREFIX)

    @app.post("/demo/fastapi/offers/send", dependencies=[Depends(require_consent("marketing"))])
    def send_offer() -> dict[str, bool]:
        return {"sent": True}

    return dpdp
