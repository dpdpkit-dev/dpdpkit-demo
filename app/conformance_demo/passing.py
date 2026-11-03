"""An app wired to dpdpkit-fastapi the documented way: the target the conformance suite passes against.

The two test headers are the convention from dpdpkit-spec; they are only read inside this throwaway app.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from dpdpkit import ConsoleNotifier, Contact
from dpdpkit.fastapi import DPDPKit
from dpdpkit.guardians import CallbackVerifier, VerifierRequest

GUARDIAN_METHODS = ("existing_kyc", "digilocker_token", "partner_token", "court_order")


def principal(request: Request) -> str | None:
    return request.headers.get("X-DPDP-Test-Principal")


def role(request: Request) -> str | None:
    return request.headers.get("X-DPDP-Test-Role")


def contact_for(who: str) -> Contact | None:
    return Contact(email=f"{who}@example.in", phone="+919800000042")


def check_guardian_token(request: VerifierRequest, evidence: Mapping[str, Any]) -> bool:
    return evidence.get("token") == "demo-ok"


def build(**overrides: Any) -> FastAPI:
    app = FastAPI(title="conformance target")
    options: dict[str, Any] = dict(
        engine=create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool),
        config=Path(__file__).parent.parent / "dpdpkit.yaml",
        principal_resolver=principal,
        admin_guard=role,
        notifier=ConsoleNotifier(),
        contact_resolver=contact_for,
        signing_key="demo-only-signing-key",
        guardian_verifiers=[CallbackVerifier(m, check_guardian_token) for m in GUARDIAN_METHODS],
        migrate_on_startup=True,
    )
    DPDPKit(**{**options, **overrides}).install(app, prefix="/dpdp")
    return app


app = build()
