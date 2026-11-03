"""Demo website: a shared layout, a home page and one page per package."""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .packages import BY_SLUG, DISCLAIMER, FICTIONAL_NOTE, PACKAGES

BASE = Path(__file__).parent

app = FastAPI(title="dpdpkit demo")
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
    return templates.TemplateResponse(request, "package.html", {"package": package})
