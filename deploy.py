"""Production entrypoint for hosted deployments.

This wraps the main Flask app and optionally makes the calculator public when
PUBLIC_ACCESS=true is set in the hosting environment.

Important: public mode means anyone with the URL can access saved sessions.
Do not store patient identifiers or PHI in public mode.
"""

from __future__ import annotations

import os

from flask import redirect, request, session, url_for

from app import app


def env_flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


@app.before_request
def public_access_override():
    if not env_flag("PUBLIC_ACCESS"):
        return None

    session["authenticated"] = True

    if request.endpoint in {"login", "logout"}:
        return redirect(url_for("dashboard"))

    return None
