"""The same app with one realistic mistake: the admin guard lets every caller in as an admin."""

from .passing import build

app = build(admin_guard=lambda request: "admin")
