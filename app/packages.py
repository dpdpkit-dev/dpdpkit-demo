"""The packages shown on the demo site, one page each.

Versions are the ones pinned in requirements.txt and package.json. A test keeps the two in step.
"""

from dataclasses import dataclass

DISCLAIMER = (
    "dpdpkit is software that helps you implement obligations under India's Digital Personal "
    "Data Protection Act, 2023 and the DPDP Rules, 2025. It does not provide legal advice and "
    "does not guarantee compliance. Decisions about notices, purposes, retention and incident "
    "reporting must be made by you or your counsel."
)

FICTIONAL_NOTE = (
    "Every name, email address, phone number and request on this site is made up. "
    "Do not enter real personal data."
)


@dataclass(frozen=True)
class Package:
    slug: str
    name: str
    registry: str  # "pypi", "npm" or "github"
    title: str
    summary: str
    demo_ticket: str  # the task that builds the live demo for this page

    @property
    def install(self) -> str:
        if self.registry == "pypi":
            return f"pip install {self.name}"
        if self.registry == "npm":
            return f"npm install {self.name}"
        return "Used from GitHub, not installed from a package registry."


PACKAGES: tuple[Package, ...] = (
    Package("fastapi", "dpdpkit-fastapi", "pypi", "FastAPI",
            "Consent, preferences and rights request endpoints for FastAPI, with @dpdpkit/react in the browser.",
            "DEMO-02"),
    Package("django", "dpdpkit-django", "pypi", "Django",
            "Template tags and consent checks for Django projects.", "DEMO-03"),
    Package("server", "dpdpkit-server", "pypi", "Any stack",
            "A standalone server, with @dpdpkit/embed added to plain HTML by script tag.", "DEMO-04"),
    Package("client", "@dpdpkit/client", "npm", "Client",
            "Typed calls to the dpdpkit API, with each request and response visible.", "DEMO-05"),
    Package("admin", "dpdpkit-admin", "github", "Admin dashboard",
            "A dashboard of requests, consent statistics and retention.", "DEMO-06"),
    Package("pii", "dpdpkit-pii", "pypi", "PII scanner",
            "Scans a dataset for personal data and reports registry gaps.", "DEMO-07"),
    Package("core", "dpdpkit-core", "pypi", "Core and policies",
            "The hash-chained ledger, retention, rule-to-code mapping and overlays "
            "(with dpdpkit-policies).", "DEMO-08"),
    Package("ci", "dpdpkit-conformance", "pypi", "CI tools",
            "dpdpkit-conformance and dpdpkit-lint-action, with passing and failing results.", "DEMO-09"),
)

BY_SLUG = {p.slug: p for p in PACKAGES}
