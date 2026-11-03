"""The live demo for the PII page: dpdpkit-pii scans a fictional database and compares it with a registry.

The dataset is a small in-memory SQLite database built at start-up from made-up people (the Aadhaar numbers carry a
valid check digit but belong to nobody). `scan_database` reads it, the visitor edits the list of registered names, and
`build_report` lists the gaps. Reports hold column names, entity types and counts, never values. The scan runs once;
only the registry diff is repeated for each request.
"""

from dataclasses import asdict

import sqlalchemy as sa
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.pool import StaticPool

from dpdpkit.pii import Report, build_report, scan_database
from dpdpkit.pii.checksums import verhoeff_check_digit

PREFIX = "/demo/pii"
FORMATS = {"json": "application/json", "md": "text/markdown", "html": "text/html"}

# What an imaginary team registered. Everything else the scan finds is a gap.
DEFAULT_REGISTRY = ("customers.full_name", "customers.email", "customers.phone", "orders.*")

PEOPLE = (
    ("Asha Verma", "asha.verma@example.com", "ABCPV1234F", "27AAPFU0939F1ZV"),
    ("Rohan Iyer", "rohan.iyer@example.com", "BCDPI2345G", "29ABCDE1234F1Z5"),
    ("Meera Nair", "meera.nair@example.com", "CDEPN3456H", "32AAACN1234C1ZX"),
    ("Kabir Singh", "kabir.singh@example.com", "DEFPS4567J", "06AABCK9876D1Z2"),
    ("Isha Patel", "isha.patel@example.com", "EFGPP5678K", "24AAECP4321A1ZB"),
    ("Dev Menon", "dev.menon@example.com", "FGHPM6789L", "33AADCD2468M1ZY"),
)


def _aadhaar(n: int) -> str:
    base = f"{2 + n % 8}{(n * 7919 + 1234567) % 10**10:010d}"[:11]
    return base + verhoeff_check_digit(base)


def _build_engine() -> sa.Engine:
    engine = sa.create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE customers (id INTEGER PRIMARY KEY, full_name TEXT, email TEXT, phone TEXT, "
            "pan TEXT, aadhaar_no TEXT, janm_tithi TEXT, notes TEXT)"
        )
        conn.exec_driver_sql("CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, upi_id TEXT, amount INTEGER)")
        conn.exec_driver_sql("CREATE TABLE vendors (id INTEGER PRIMARY KEY, name TEXT, gstin TEXT, ifsc TEXT, contact_mobile TEXT)")
        conn.exec_driver_sql("CREATE TABLE products (id INTEGER PRIMARY KEY, title TEXT, price INTEGER)")
        for i, (name, email, pan, gstin) in enumerate(PEOPLE, start=1):
            handle = name.split()[0].lower()
            conn.exec_driver_sql(
                "INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (i, name, email, f"9{i}00000{i}{i}{i}", pan, _aadhaar(i), f"199{i}-0{i}-1{i}", "called back on the same day"),
            )
            conn.exec_driver_sql("INSERT INTO orders VALUES (?, ?, ?, ?)", (i, i, f"{handle}@okbank", 400 * i))
            conn.exec_driver_sql(
                "INSERT INTO vendors VALUES (?, ?, ?, ?, ?)",
                (i, f"{name.split()[1]} Traders", gstin, f"HDFC0{i:06d}", f"8{i}12345{i}0{i}"),
            )
            conn.exec_driver_sql("INSERT INTO products VALUES (?, ?, ?)", (i, f"Notebook pack {i}", 90 + i))
    return engine


def _registry(text: str) -> list[str]:
    return [line.strip() for line in text.replace(",", "\n").splitlines() if line.strip()]


def install(app: FastAPI) -> None:
    scan = scan_database(_build_engine(), sample=100)

    def report(text: str) -> Report:
        return build_report(scan, registry=_registry(text))

    def registry_text(request: Request) -> str:
        return request.query_params.get("registry", "\n".join(DEFAULT_REGISTRY))

    @app.get(f"{PREFIX}/report")
    def download(request: Request, format: str = "json") -> PlainTextResponse:
        if format not in FORMATS:
            format = "json"
        return PlainTextResponse(report(registry_text(request)).render(format), media_type=FORMATS[format])

    app.state.pii_report = lambda request: (registry_text(request), report(registry_text(request)))


def view(app: FastAPI, request: Request) -> dict:
    text, rep = app.state.pii_report(request)
    return {
        "pii_registry": text,
        "pii_summary": rep.summary,
        "pii_rows": [asdict(r) | {"detected": r.detected} for r in rep.rows],
        "pii_unmatched": rep.unmatched,
        "pii_markdown": rep.to_markdown(),
        "pii_prefix": PREFIX,
    }
