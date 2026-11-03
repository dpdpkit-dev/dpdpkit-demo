# dpdpkit-demo

Demo website for dpdpkit: a shared layout, a home page and one page per package.

> **Disclaimer.** dpdpkit is software that helps you implement obligations under India's Digital Personal
> Data Protection Act, 2023 and the DPDP Rules, 2025. It does not provide legal advice and does not
> guarantee compliance. Decisions about notices, purposes, retention and incident reporting must be made
> by you or your counsel.

All data on the site is fictional. The disclaimer appears in the footer of every page.

## Packages come from the registries

Python packages are pinned in `requirements.txt` (PyPI) and npm packages in `package.json`. The site never
imports from sibling checkouts. `@dpdpkit/embed` is not on npm yet and `dpdpkit-admin` is a GitHub release
bundle, so neither is installed here; their pages say so and are filled in by DEMO-04 and DEMO-06.

## Run

```
python -m venv .venv && .venv/Scripts/activate   # source .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
pytest -q
```

Pages: `/` and `/packages/<slug>` for `fastapi`, `django`, `server`, `client`, `admin`, `pii`, `core`, `ci`.
