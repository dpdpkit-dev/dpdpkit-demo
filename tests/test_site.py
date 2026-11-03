import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.packages import DISCLAIMER, PACKAGES

ROOT = Path(__file__).parent.parent
client = TestClient(app)
PATHS = ["/"] + [f"/packages/{p.slug}" for p in PACKAGES]


@pytest.mark.parametrize("path", PATHS)
def test_page_renders_with_disclaimer(path):
    r = client.get(path)
    assert r.status_code == 200
    assert "does not provide legal advice" in r.text
    assert "made up" in r.text


def test_home_links_every_package():
    html = client.get("/").text
    for p in PACKAGES:
        assert f'href="/packages/{p.slug}"' in html


def test_unknown_package_is_404():
    assert client.get("/packages/nope").status_code == 404


def test_disclaimer_matches_shared_text():
    shared = ROOT.parent / "_shared" / "DISCLAIMER.md"
    if not shared.exists():
        pytest.skip("not checked out inside the dpdpkit workspace")
    text = re.sub(r"\s*\n>\s*", " ", shared.read_text(encoding="utf-8").replace("> ", "", 1)).strip()
    assert DISCLAIMER in text


def test_dependencies_come_from_registries():
    reqs = (ROOT / "requirements.txt").read_text()
    pkg = json.loads((ROOT / "package.json").read_text())
    specs = [l for l in reqs.splitlines() if l.strip() and not l.startswith("#")]
    for spec in specs + [f"{k}@{v}" for k, v in pkg["dependencies"].items()]:
        assert not re.search(r"(^-e|file:|\.\./|@ |link:|git\+)", spec), spec
    for name in ("dpdpkit-core", "dpdpkit-fastapi", "dpdpkit-django", "dpdpkit-server", "dpdpkit-pii"):
        assert any(s.startswith(f"{name}==") for s in specs), name
    assert set(pkg["dependencies"]) == {"@dpdpkit/client", "@dpdpkit/react"}
