"""Demo website: a shared layout, a home page and one page per package."""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import admin_demo, ci_demo, core_demo, django_demo, fastapi_demo, pii_demo, server_demo
from .packages import BY_SLUG, DISCLAIMER, FICTIONAL_NOTE, PACKAGES

BASE = Path(__file__).parent

app = FastAPI(title="dpdpkit demo")
fastapi_demo.install(app)
django_demo.install(app)
server_demo.install(app)
admin_demo.install(app)
pii_demo.install(app)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")
templates.env.globals.update(packages=PACKAGES, disclaimer=DISCLAIMER, fictional_note=FICTIONAL_NOTE)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "home.html")


@app.get("/packages/{slug}", response_class=HTMLResponse)
def package_page(request: Request, slug: str):
    package = BY_SLUG.get(slug)
    if package is None:
        raise HTTPException(status_code=404)
    context = {"package": package, "demo_users": fastapi_demo.DEMO_USERS, "demo_prefix": fastapi_demo.PREFIX,
               "django_prefix": django_demo.PREFIX, "server_prefix": server_demo.PREFIX,
               "admin_ui": f"{admin_demo.PREFIX}{admin_demo.UI_PATH}/"}
    if slug == "ci":
        context.update(ci_demo.view(request))
    if slug == "core":
        context.update(core_demo.view(request))
    if slug == "pii":
        context.update(pii_demo.view(app, request))
    return templates.TemplateResponse(request, "package.html", context)
