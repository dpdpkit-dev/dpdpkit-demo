"""The live demo for the Django page: a small Django project running dpdpkit-django, mounted on this site.

Django serves server-rendered pages at /demo/django/ using the `{% dpdp_notice %}` and `{% dpdp_preferences %}`
template tags and the `@requires_consent` / `RequiresConsentMixin` checks.
"""

import os

from fastapi import FastAPI

PREFIX = "/demo/django"


def install(app: FastAPI) -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.django_demo.settings")
    from django.core.asgi import get_asgi_application
    from django.core.management import call_command

    django_app = get_asgi_application()  # sets Django up
    call_command("migrate", verbosity=0)
    app.mount(PREFIX, django_app)
