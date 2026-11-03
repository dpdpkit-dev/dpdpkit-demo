"""Views for the Django page: the template tags, `record_preferences` and both consent checks."""

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views import View
from django.views.decorators.http import require_POST
from dpdpkit.errors import DpdpkitError
from dpdpkit.django import conf
from dpdpkit.django.consent import RequiresConsentMixin, record_preferences, requires_consent

from ..fastapi_demo import DEMO_USERS
from ..packages import DISCLAIMER, FICTIONAL_NOTE

COOKIE = "demo_user"


def site_context(request: HttpRequest) -> dict[str, str]:
    """The site-wide disclaimer, so these pages carry it like every other page."""
    return {"disclaimer": DISCLAIMER, "fictional_note": FICTIONAL_NOTE}


def current_user(request: HttpRequest) -> str | None:
    user = request.COOKIES.get(COOKIE)
    return user if user in DEMO_USERS else None


def denied(request: HttpRequest, error: DpdpkitError) -> HttpResponse:
    """What a failed consent check shows: the 401 or 403 the check raised, as a page."""
    status = 401 if error.code == "unauthenticated" else 403
    return render(request, "django_demo/result.html", {"ok": False, "error": error}, status=status)


def _states(request: HttpRequest) -> list:
    principal = current_user(request)
    return conf.get_kit().consent.state(principal) if principal else []


def index(request: HttpRequest) -> HttpResponse:
    user = current_user(request)
    context = {
        "users": DEMO_USERS,
        "user_id": user,
        "user": DEMO_USERS.get(user),
        "locale": "hi" if request.GET.get("lang") == "hi" else "en",
        "states": _states(request),
    }
    return render(request, "django_demo/index.html", context)


def act_as(request: HttpRequest, user_id: str) -> HttpResponse:
    if user_id not in DEMO_USERS:
        raise Http404
    response = redirect("index")
    response.set_cookie(COOKIE, user_id, samesite="Lax")
    return response


@require_POST
def preferences(request: HttpRequest) -> HttpResponse:
    record_preferences(request)  # the form posted by {% dpdp_preferences %}
    return redirect("index")


@require_POST
@requires_consent("marketing", on_denied=denied)
def send_offer(request: HttpRequest) -> HttpResponse:
    return render(request, "django_demo/result.html", {"ok": True, "what": "The offer was sent."})


class DigestView(RequiresConsentMixin, View):
    """The class-based version of the same check."""

    consent_purposes = ("marketing",)

    def consent_denied(self, request: HttpRequest, error: DpdpkitError) -> HttpResponse:
        return denied(request, error)

    def post(self, request: HttpRequest) -> HttpResponse:
        return render(request, "django_demo/result.html", {"ok": True, "what": "The weekly digest was queued."})
