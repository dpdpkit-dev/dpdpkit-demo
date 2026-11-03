"""The live demo for the core page: dpdpkit-core and dpdpkit-policies, with no web framework or database in between.

Every request builds a small kit on an in-memory repository, seeded with fictional people. Nothing is shared between
visitors, so there is nothing to reset. Four sections:

- ledger: `ledger.verify_report()` on untouched rows, then after the visitor edits, deletes or truncates one. A tail
  truncation is invisible to `verify()` alone; it shows up against the root hash exported before the change.
- retention: `retention.preview()` for people whose inactivity clocks are at different stages.
- rule to code: `load_rule_map()` joined with the values in the pack the visitor has chosen.
- overlays: `Policy.load(pack, overlays)` and `Policy.diff()` against the base pack.
"""

import datetime as dt
import json
from pathlib import Path

from fastapi import Request

from dpdpkit import InMemoryRepository, Policy, kit_from_config, load_config, sync_notice
from dpdpkit_policies import list_overlays, list_packs, load_rule_map

CONFIG = Path(__file__).parent / "dpdpkit.yaml"
TAMPERS = {
    "none": "Leave the ledger alone",
    "edit": "Edit one consent row (change its purpose)",
    "delete": "Delete a row from the middle",
    "truncate": "Cut the last two rows off the end",
}
PEOPLE = ("u_asha", "u_vikram", "u_meera", "u_kabir")
# Days since each person's last activity; the "account" purpose erases after 1095 days of inactivity.
INACTIVE_DAYS = {"u_asha": 5, "u_vikram": 1050, "u_meera": 1090, "u_kabir": 1100}


def _shown(value: object) -> str:
    return json.dumps(value) if isinstance(value, (dict, list)) else str(value)


def _kit(clock: list[dt.datetime]):
    config = load_config(CONFIG)
    kit = kit_from_config(config, InMemoryRepository(), signing_key="demo-only-signing-key", clock=lambda: clock[0])
    sync_notice(kit, config)
    return kit


def ledger_section(tamper: str) -> dict:
    clock = [dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=10)]
    kit = _kit(clock)
    for person in PEOPLE:
        clock[0] += dt.timedelta(hours=6)
        kit.consent.record(person, {"account": True, "marketing": person != "u_kabir"})
    clock[0] = dt.datetime.now(dt.timezone.utc)
    kit.consent.withdraw("u_asha", "marketing")
    root = kit.ledger.root_hash()  # what an operator would have exported to storage they cannot rewrite
    rows = kit.repository.consent_events
    before = len(rows)
    if tamper == "edit":
        rows[2] = rows[2].model_copy(update={"purpose": "marketing" if rows[2].purpose != "marketing" else "account"})
    elif tamper == "delete":
        del rows[3]
    elif tamper == "truncate":
        del rows[-2:]
    report = kit.ledger.verify_report()
    now_root = kit.ledger.root_hash()
    return {
        "tamper": tamper,
        "rows_before": before,
        "rows_after": len(rows),
        "report": report.model_dump(mode="json"),
        "root_matches": now_root.root == root.root,
        "root_exported": root.root,
        "root_now": now_root.root,
    }


def retention_section(horizon_days: int) -> dict:
    clock = [dt.datetime.now(dt.timezone.utc)]
    kit = _kit(clock)
    now = clock[0]
    for person, idle in INACTIVE_DAYS.items():
        kit.retention.record_activity(person, now - dt.timedelta(days=idle))
    items = kit.retention.preview(now, dt.timedelta(days=horizon_days))
    return {
        "horizon": horizon_days,
        "warn_hours": int(kit.policy.erasure_pre_notice.total_seconds() // 3600),
        "log_days": kit.policy.min_log_retention.days,
        "items": [
            {"principal": i.principal, "purpose": i.purpose, "action": i.action, "at": i.at.strftime("%Y-%m-%d %H:%M"),
             "status": i.status.value}
            for i in items
        ],
        "people": INACTIVE_DAYS,
    }


def policy_section(pack: str, chosen: list[str]) -> dict:
    base = Policy.load(pack)
    policy = Policy.load(pack, chosen)
    rules = []
    for rule in load_rule_map():
        value = policy.get(rule["key"], None)
        rules.append(rule | {"value": "(overlay only, not enabled)" if value is None else _shown(value),
                             "from_overlay": value is not None and base.get(rule["key"], None) != value})
    return {
        "pack": pack,
        "packs": list_packs(),
        "overlays_available": list_overlays(),
        "overlays_chosen": chosen,
        "rules": rules,
        "changes": [{"key": c.key, "old": "-" if c.old is None else _shown(c.old), "new": _shown(c.new)}
                    for c in base.diff(policy)],
    }


def view(request: Request) -> dict:
    q = request.query_params
    tamper = q.get("tamper", "none")
    try:
        horizon = max(0, min(int(q.get("horizon", "7")), 1500))
    except ValueError:
        horizon = 7
    packs = list_packs()
    pack = q.get("pack") if q.get("pack") in packs else packs[-1]
    chosen = [o for o in q.getlist("overlay") if o in list_overlays()]
    return {
        "core_tampers": TAMPERS,
        "core_ledger": ledger_section(tamper if tamper in TAMPERS else "none"),
        "core_retention": retention_section(horizon),
        "core_policy": policy_section(pack, chosen),
    }
