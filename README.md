# dpdpkit-demo

Demo website for dpdpkit: a shared layout, a home page and one page per package.

> **Disclaimer.** dpdpkit is software that helps you implement obligations under India's Digital Personal
> Data Protection Act, 2023 and the DPDP Rules, 2025. It does not provide legal advice and does not
> guarantee compliance. Decisions about notices, purposes, retention and incident reporting must be made
> by you or your counsel.

All data on the site is fictional. The disclaimer appears in the footer of every page.

## Packages come from the registries

Python packages are pinned in `requirements.txt` (PyPI) and npm packages in `package.json`. The site never
imports from sibling checkouts. `dpdpkit-admin` is a GitHub release bundle, so the admin bundle is downloaded
from its GitHub release (see below). The embed bundle is copied from the `@dpdpkit/embed` npm package.

## FastAPI page

`/packages/fastapi` runs the published `dpdpkit-fastapi` backend (mounted at `/demo/fastapi/dpdp`, in-memory
SQLite, config in `app/dpdpkit.yaml`) with `@dpdpkit/react` showing the consent notice, preference centre and
rights request form. The page's "Act as" select picks one of two fictional users and sends it in the `X-User`
header. The React bundle is built from `frontend/` into `app/static/dist` (not committed), so run
`npm install && npm run build` before starting the site.

## Django page

`/packages/django` frames a small Django project (`app/django_demo/`) running the published `dpdpkit-django`,
mounted on this site at `/demo/django/` through Django's ASGI app and reusing `app/dpdpkit.yaml`. It is
server-rendered: `{% dpdp_notice %}` and `{% dpdp_preferences %}` show the notice and the consent form, and two
views are guarded by `@requires_consent("marketing")` and `RequiresConsentMixin`. The "Act as" links set a
cookie naming one of the two fictional users. The database is a temporary SQLite file, removed on exit.

## Any-stack page

`/packages/server` frames a plain HTML page (`app/server_demo/page.html`) that loads `@dpdpkit/embed` with a
script tag and uses `<dpdp-consent>`, `<dpdp-preferences>` and `<dpdp-rights-form>`. The published `dpdpkit-server`
app runs in this process at `/demo/server/api`, with a temporary SQLite database. The routes under
`/demo/server/backend` play the page's own backend: they hold the server's API key (new on every start), read the
"Act as" cookie and mint the short-lived token the widgets fetch through `token-url`. `npm run build` copies the
published embed bundle to `app/static/dist/embed.js`.

## Client page

`/packages/client` uses `@dpdpkit/client` on its own, with no components, against the FastAPI demo backend at
`/demo/fastapi/dpdp`. `frontend/client-demo.js` passes the client a custom `fetch`, so each request (method, URL,
headers, body) and response (status, body) is printed in a log, and a failure shows the `DpdpError` code. Each
button runs one client call. The "Act as" select sets the `X-User` header.

## Admin page

`/packages/admin` frames the `dpdpkit-admin` dashboard. A second `dpdpkit-fastapi` backend (`app/admin_demo.py`, own
in-memory database, mounted as a sub-app at `/demo/admin/dpdp`) is seeded at start-up with fictional consent
decisions, rights requests at different stages (including near-deadline and overdue ones), retention erasures due
within a week and one incident. The admin guard gives every visitor the admin role, which is fine only because the
data is fictional. The published wheel carries a placeholder dashboard page, so `npm run build` runs
`scripts/fetch_admin_bundle.py`, which downloads the release pinned in `admin-bundle.version`, checks its sha256
and unpacks it to `app/static/dist/admin`; the site serves it at `/demo/admin/dpdp/admin/ui/`.

## PII page

`/packages/pii` runs `dpdpkit-pii` on a fictional in-memory SQLite database built at start-up by `app/pii_demo.py`
(customers, orders, vendors and products with made-up PAN, Aadhaar, GSTIN, IFSC, UPI and mobile values). The scan runs
once; the visitor edits a list of registered names (`table.column`, `*` wildcards) and the page rebuilds the registry
diff, showing the gaps first, the registry entries that matched nothing, and the report. The report can be downloaded
as JSON, Markdown or HTML from `/demo/pii/report`. Reports hold names, entity types and counts, never values.

## Core page

`/packages/core` calls `dpdpkit-core` and `dpdpkit-policies` directly (`app/core_demo.py`). Each request builds a small
kit on an in-memory repository seeded with fictional people, so nothing is stored or shared between visitors. Query
parameters drive four sections: `tamper` (`none`, `edit`, `delete`, `truncate`) edits the consent rows and re-runs
`ledger.verify_report()`, with a tail truncation caught only by the root hash taken before the change; `horizon` sets
the days for `retention.preview()`; `pack` and `overlay` (repeatable) pick what `Policy.load()` merges, with
`Policy.diff()` listing the changes; and the rule-to-code table joins `load_rule_map()` with the chosen pack's values.

## CI tools page

`/packages/ci` runs both CI tools for real (`app/ci_demo.py`). The lint section calls `run_lint()`, the function behind
`dpdpkit lint` and `dpdpkit-lint-action`, on a sample config (`sample`: `good`, `missing-retention`, `no-notice`, derived
from `app/lint_samples/good.yaml`) or on text the visitor edits (`config`); `strict=1` also fails on warnings. It shows the
job-log output, the GitHub annotations and the exit code. The conformance section (`target`: `passing` or `failing`)
runs `python -m dpdpkit_conformance` as a subprocess against the apps in `app/conformance_demo/`; the failing one lets
every caller in as an admin. Each target runs once per process and its per-test results are cached.

## Deploy

The whole site is one container (`Dockerfile`, `docker-compose.yml`): a Node stage builds the React, embed and admin
bundles and the Python stage runs `uvicorn app.main:app`. Every backend the pages frame runs in that process, so one
service is all a host needs. It reads the port from `PORT` (default 8000). It runs on Render's free plan from
`render.yaml` (dashboard: New > Blueprint), which deploys `main` after CI passes. Any host that runs a container works.

- **Data reset.** All demo data is in memory or in temporary files and is seeded at start-up. `DEMO_RESET_HOURS`
  (24 in the image, 0 = off) makes the process exit after that long and the restart policy (`restart: always`) brings it
  back with fresh data. On a host without a restart policy, restart the service on a schedule instead.
- **Rate limits.** `app/ops.py` limits each client per minute: `DEMO_RATE_READ` (240) for reads and `DEMO_RATE_WRITE`
  (60) for POST/PUT/PATCH/DELETE; 0 turns a limit off. Over the limit gets a 429 with `Retry-After`. Static files and
  `/healthz` are exempt. Behind a proxy, set `DEMO_CLIENT_IP_HEADER` to a header it always overwrites (`CF-Connecting-IP`
  on Render), or `DEMO_TRUST_PROXY=1` to use the first `X-Forwarded-For` entry if the proxy overwrites that header. Limits are per process, which is right for a single container.
- **Health.** `GET /healthz` returns `{"status": "ok"}`.
- **Smoke test.** `python scripts/smoke.py <url> [--wait 60]` loads the home page and every package page, checks the
  disclaimer, the admin dashboard, the PII report and every `/static/` asset the pages reference. The `ci` workflow runs
  it against a local server and against the built image on every push and daily; `smoke-live` runs it against the
  repository variable `DEMO_URL` every six hours and does nothing until that is set.


## Run

```
python -m venv .venv && .venv/Scripts/activate   # source .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt
npm install && npm run build                     # the React demos
uvicorn app.main:app --reload
pytest -q
```

Pages: `/` and `/packages/<slug>` for `fastapi`, `django`, `server`, `client`, `admin`, `pii`, `core`, `ci`.
