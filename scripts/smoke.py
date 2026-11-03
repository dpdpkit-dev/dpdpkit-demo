#!/usr/bin/env python3
"""Smoke test for a running demo site: every page loads, shows the disclaimer, and its local assets load.

Usage: scripts/smoke.py <base url> [--wait SECONDS]
Exits 1 and lists every failure. Needs only the standard library, so it can run against the live site too.
"""

import argparse
import re
import sys
import time
import urllib.error
import urllib.request

SLUGS = ["fastapi", "django", "server", "client", "admin", "pii", "core", "ci"]
PAGES = ["/"] + [f"/packages/{slug}" for slug in SLUGS]
# Extra endpoints behind the pages: the health check, the admin dashboard bundle and the PII report download.
EXTRAS = ["/healthz", "/demo/admin/dpdp/admin/ui/", "/demo/pii/report"]
ASSET = re.compile(r'(?:src|href)="(/static/[^"#?]+)')


def get(base: str, path: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(base + path, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        return 0, str(e)


def wait_ready(base: str, seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while get(base, "/healthz")[0] != 200:
        if time.monotonic() > deadline:
            sys.exit(f"{base} did not become healthy within {seconds:.0f}s")
        time.sleep(1)


def run(base: str) -> list[str]:
    failures, assets = [], set()
    for path in PAGES:
        status, body = get(base, path)
        if status != 200:
            failures.append(f"{path}: HTTP {status}")
            continue
        if "does not provide legal advice" not in body:
            failures.append(f"{path}: disclaimer missing")
        assets.update(ASSET.findall(body))
    for path in EXTRAS + sorted(assets):
        status, _ = get(base, path)
        if status != 200:
            failures.append(f"{path}: HTTP {status}")
    print(f"checked {len(PAGES)} pages, {len(EXTRAS)} endpoints, {len(assets)} assets")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("base")
    parser.add_argument("--wait", type=float, default=0, help="seconds to wait for /healthz first")
    args = parser.parse_args()
    base = args.base.rstrip("/")
    if args.wait:
        wait_ready(base, args.wait)
    failures = run(base)
    for line in failures:
        print("FAIL", line)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
