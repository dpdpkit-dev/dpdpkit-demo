"""The live demo for the admin page: the dpdpkit-admin dashboard on a seeded dpdpkit-fastapi backend.

A second dpdpkit-fastapi instance runs at /demo/admin/dpdp with its own in-memory SQLite database. It is filled at
start-up with fictional people: consent decisions, rights requests at different stages (some close to or past their
deadline), an incident, and last-activity dates that put erasures on the retention monitor. The clock is moved back
while seeding, then runs normally.

The dashboard itself is the dpdpkit-admin release bundle, which the published wheel does not carry yet (it ships a
placeholder page), so `npm run build` downloads the pinned release into app/static/dist/admin and this module serves
it at /demo/admin/dpdp/admin/ui/. Anyone can open the dashboard: there is no real data here, so the admin guard grants
every visitor the admin role, and visitors can change the seeded requests until the site restarts.
"""

import datetime as dt
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from starlette.staticfiles import StaticFiles

from dpdpkit import ConsoleNotifier
from dpdpkit.models import IncidentSeverity
from dpdpkit.fastapi import DPDPKit

PREFIX = "/demo/admin"
API_PREFIX = "/dpdp"  # inside the sub-app, so the API is at /demo/admin/dpdp
UI_PATH = f"{API_PREFIX}/admin/ui"
BUNDLE = Path(__file__).parent / "static" / "dist" / "admin"


class _Clock:
    """UTC now, moved back by `back` while the demo data is seeded."""

    def __init__(self) -> None:
        self.back = dt.timedelta(0)

    def __call__(self) -> dt.datetime:
        return dt.datetime.now(dt.timezone.utc) - self.back


def _days(n: float) -> dt.timedelta:
    return dt.timedelta(days=n)


def seed(dpdp: DPDPKit, clock: _Clock) -> None:
    """Fictional people only. Requests are opened in the past so the queue shows near and overdue deadlines."""
    kit = dpdp.kit
    staff = "staff:meera"

    # Consent: a mix of grants and withdrawals, so the statistics have something to count.
    people = {
        "u_asha": (True, 120), "u_vikram": (True, 90), "u_meera": (True, 75), "u_kabir": (False, 60),
        "u_isha": (True, 45), "u_dev": (True, 30), "u_naina": (False, 20), "u_rohan": (True, 10),
    }
    for person, (marketing, age) in people.items():
        clock.back = _days(age)
        kit.consent.record(person, {"account": True, "marketing": marketing})
    for person, age in (("u_dev", 12), ("u_isha", 5)):  # these two later withdraw marketing
        clock.back = _days(age)
        kit.consent.withdraw(person, "marketing")

    # Rights requests at different stages.
    clock.back = _days(40)  # opened long ago and still open: overdue
    kit.rights.open("u_kabir", "erasure", {"reason": "I no longer shop here"})
    clock.back = _days(26)  # close to the deadline
    kit.rights.open("u_naina", "access")
    clock.back = _days(9)
    req = kit.rights.open("u_asha", "correction", {"field": "phone", "new_value": "+919800000099"})
    kit.rights.assign(req.id, "meera", actor=staff)
    kit.rights.verify_identity(req.id, True, actor=staff, method="otp")
    clock.back = _days(6)
    kit.rights.open("u_rohan", "grievance", {"text": "The offer email arrived after I withdrew consent."})
    clock.back = _days(3)
    req = kit.rights.open("u_vikram", "access")
    kit.rights.assign(req.id, "meera", actor=staff)
    clock.back = _days(2)
    kit.rights.open("u_meera", "nomination", {"name": "Anil Rao", "contact": "anil@example.in"})
    clock.back = _days(20)  # one that is already finished
    req = kit.rights.open("u_isha", "access")
    kit.rights.verify_identity(req.id, True, actor=staff, method="otp")
    kit.rights.respond(req.id, "Your data export was emailed to you.", actor=staff)

    # Retention: activity far enough back that the 3-year account erasures fall inside the next week.
    clock.back = _days(0)
    for person, age in (("u_kabir", 1090), ("u_naina", 1092)):
        kit.retention.record_activity(person, clock() - _days(age))

    # One incident, aware about a day ago, so its notification clocks are running.
    clock.back = _days(1)
    kit.incidents.record(
        "Exposed order export",
        actor=staff,
        severity=IncidentSeverity.MEDIUM,
        description="A staging export of order history was reachable without sign-in for about two hours.",
        affected_count=120,
        data_items=["email", "order_history"],
        root_cause="Storage bucket was left public after a test.",
        remediation="Bucket closed; access logs are being reviewed.",
    )
    clock.back = _days(0)


def install(app: FastAPI) -> DPDPKit:
    clock = _Clock()
    dpdp = DPDPKit(
        engine=create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool),
        config=Path(__file__).with_name("dpdpkit.yaml"),
        principal_resolver=lambda request: "demo-visitor",
        admin_guard=lambda request: "admin",
        notifier=ConsoleNotifier(),
        signing_key="demo-only-signing-key",
        migrate_on_startup=True,
        clock=clock,
    )
    seed(dpdp, clock)
    # A sub-app of its own, so this instance does not replace the FastAPI page's app.state.dpdpkit.
    sub = FastAPI(title="dpdpkit admin demo")
    if (BUNDLE / "index.html").exists():  # DPDPKit.install keeps an existing mount at the path
        sub.mount(UI_PATH, StaticFiles(directory=BUNDLE, html=True), name="admin-ui")
    dpdp.install(sub, prefix=API_PREFIX, admin_path=UI_PATH, track_activity=False)
    app.mount(PREFIX, sub)
    return dpdp
