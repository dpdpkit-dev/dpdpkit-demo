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
    assert set(pkg["dependencies"]) == {"@dpdpkit/client", "@dpdpkit/embed", "@dpdpkit/react"}


def test_fastapi_page_mounts_the_react_demo():
    html = client.get("/packages/fastapi").text
    assert 'id="fastapi-demo"' in html
    assert "/static/dist/fastapi-demo.js" in html
    assert "coming (DEMO-02)" not in html


def test_fastapi_demo_consent_preferences_and_rights_flows():
    base, who = "/demo/fastapi", {"X-User": "u_vikram"}
    with TestClient(app) as c:  # the context manager runs startup, which migrates the database
        notice = c.get(f"{base}/dpdp/notices/current", headers=who).json()
        assert {p["id"] for p in notice["purposes"]} == {"account", "marketing"}
        assert c.post(f"{base}/offers/send", headers=who).status_code == 403  # nothing pre-ticked

        granted = c.post(f"{base}/dpdp/consents", headers=who,
                         json={"decisions": [{"purpose": "marketing", "granted": True}]})
        assert granted.status_code == 201
        assert c.post(f"{base}/offers/send", headers=who).status_code == 200

        withdrawn = c.post(f"{base}/dpdp/consents/marketing/withdraw", headers=who)
        assert withdrawn.json()["status"] == "withdrawn"
        assert c.post(f"{base}/offers/send", headers=who).status_code == 403

        opened = c.post(f"{base}/dpdp/requests", headers=who, json={"kind": "access"})
        assert opened.status_code == 201
        assert [r["id"] for r in c.get(f"{base}/dpdp/requests", headers=who).json()["items"]] == [opened.json()["id"]]

        assert c.get(f"{base}/dpdp/consents/me").status_code == 401  # unknown users are not signed in


def test_django_page_embeds_the_django_demo():
    html = client.get("/packages/django").text
    assert 'src="/demo/django/"' in html
    assert "coming (DEMO-03)" not in html


def test_django_demo_template_tags_and_consent_checks():
    base = "/demo/django"
    with TestClient(app) as c:
        anon = c.get(f"{base}/")
        assert anon.status_code == 200
        assert 'class="dpdp-notice"' in anon.text  # {% dpdp_notice %}
        assert "does not provide legal advice" in anon.text
        assert 'class="dpdp-preferences"' not in anon.text  # needs someone signed in
        token = c.cookies["csrftoken"]
        post = lambda path: c.post(f"{base}{path}", data={"csrfmiddlewaretoken": token}, headers={"X-CSRFToken": token})
        assert post("/offers/send/").status_code == 401

        assert c.get(f"{base}/act-as/u_vikram/", follow_redirects=False).status_code == 302
        assert c.get(f"{base}/act-as/nobody/").status_code == 404
        page = c.get(f"{base}/")
        assert 'class="dpdp-preferences"' in page.text  # {% dpdp_preferences %}
        assert "checked" not in page.text  # nothing pre-ticked
        assert 'हम आपके' in c.get(f"{base}/?lang=hi").text

        assert post("/offers/send/").status_code == 403  # decorator
        assert post("/offers/digest/").status_code == 403  # mixin

        saved = c.post(f"{base}/preferences/", data={"purpose": ["marketing"], "notice_version": "1", "locale": "en",
                                                     "csrfmiddlewaretoken": token}, follow_redirects=False)
        assert saved.status_code == 302
        assert post("/offers/send/").status_code == 200
        assert post("/offers/digest/").status_code == 200
        assert "checked" in c.get(f"{base}/").text

        c.post(f"{base}/preferences/", data={"notice_version": "1", "locale": "en", "csrfmiddlewaretoken": token})
        assert post("/offers/send/").status_code == 403  # unticking withdraws


def test_server_page_embeds_the_plain_html_demo():
    html = client.get("/packages/server").text
    assert 'src="/demo/server/"' in html
    assert "coming (DEMO-04)" not in html


def test_server_demo_is_plain_html_with_the_embed_script_tag():
    page = client.get("/demo/server/").text
    assert '<script src="/static/dist/embed.js"></script>' in page
    for tag in ("dpdp-consent", "dpdp-preferences", "dpdp-rights-form"):
        assert f"<{tag} " in page
    assert 'type="module"' not in page and "{{" not in page
    assert "does not provide legal advice" in page
    assert client.get("/static/dist/embed.js").status_code == 200  # copied by `npm run build`


def test_server_demo_token_flow_and_widget_api():
    base = "/demo/server"
    with TestClient(app) as c:
        assert c.post(f"{base}/backend/privacy-token").status_code == 401  # nobody signed in
        assert c.get(f"{base}/backend/act-as/nobody").status_code == 404
        c.get(f"{base}/backend/act-as/u_asha", follow_redirects=False)
        issued = c.post(f"{base}/backend/privacy-token")
        assert issued.status_code == 200
        who = {"Authorization": f"Bearer {issued.json()['token']}"}
        api = f"{base}/api/dpdp"

        assert c.get(f"{api}/consents/me").status_code == 401  # a widget call needs the token
        notice = c.get(f"{api}/notices/current", headers=who).json()
        assert {p["id"] for p in notice["purposes"]} == {"account", "marketing"}
        granted = c.post(f"{api}/consents", headers=who, json={"decisions": [{"purpose": "marketing", "granted": True}]})
        assert granted.status_code == 201
        opened = c.post(f"{api}/requests", headers=who, json={"kind": "access"})
        assert opened.status_code == 201
        assert [r["id"] for r in c.get(f"{api}/requests", headers=who).json()["items"]] == [opened.json()["id"]]
        assert c.post(f"{base}/api/v1/tokens", json={"subject": "u_asha"}).status_code == 401  # needs the API key


def test_client_page_mounts_the_logging_demo():
    html = client.get("/packages/client").text
    assert 'id="client-demo"' in html and "/static/dist/client-demo.js" in html
    assert "coming (DEMO-05)" not in html
    assert client.get("/static/dist/client-demo.js").status_code == 200  # built by `npm run build`


def test_client_demo_calls_hit_the_fastapi_backend_the_client_paths():
    # The paths @dpdpkit/client builds for the buttons on the page, against the backend it points at.
    base = "/demo/fastapi/dpdp"
    who = {"X-User": "u_vikram"}
    assert client.get(f"{base}/notices/current", params={"locale": "en"}, headers=who).status_code == 200
    granted = client.post(f"{base}/consents", headers=who, json={"decisions": [{"purpose": "marketing", "granted": True}]})
    assert granted.status_code == 201
    assert client.get(f"{base}/consents/me/receipt", headers=who).status_code == 200
    assert client.post(f"{base}/consents/marketing/withdraw", headers=who).status_code == 200
    assert client.post(f"{base}/requests", headers=who, json={"kind": "access", "details": {}}).status_code == 201
    assert client.get(f"{base}/me/export", headers=who).status_code == 200
    assert client.get(f"{base}/consents/me").status_code == 401  # DpdpError path: nobody signed in
