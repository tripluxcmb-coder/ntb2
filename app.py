"""Python backend for the company-first relationship dashboard."""
from __future__ import annotations

import os
import hmac
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request
from banker.data import DataError
from banker.branding import logo_data_uri
from banker.reporting import position_svg
from banker.service import BankService

ROOT = Path(__file__).resolve().parent


def create_app(settings: dict | None = None, *, service: BankService | None = None) -> Flask:
    load_dotenv(ROOT / ".env")
    # Vercel serves public/** from its CDN. Using the same directory as Flask's
    # local static folder keeps local and deployed URLs identical.
    app = Flask(__name__, static_folder="public", static_url_path="")
    app.config.update(MAX_CONTENT_LENGTH=16 * 1024, JSON_SORT_KEYS=False)
    app.config.update(settings or {})
    bank = service or BankService(ROOT)
    app.extensions["bank_service"] = bank

    def enabled(name: str) -> bool:
        return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}

    access_required = enabled("REQUIRE_ACCESS_AUTH") or enabled("VERCEL")
    access_username = os.getenv("APP_ACCESS_USERNAME", "bank-officer")
    access_password = os.getenv("APP_ACCESS_PASSWORD", "")

    @app.before_request
    def deployment_access_control():
        # This lightweight guard prevents an accidental public exposure. Replace
        # it with the bank's SSO and CIF entitlements before production use.
        if not access_required or request.path == "/health":
            return None
        if not access_password:
            return Response(
                "Deployment access protection is not configured.",
                status=503,
                mimetype="text/plain",
                headers={"Cache-Control": "no-store"},
            )
        auth = request.authorization
        valid = bool(
            auth
            and hmac.compare_digest(auth.username or "", access_username)
            and hmac.compare_digest(auth.password or "", access_password)
        )
        if not valid:
            return Response(
                "Authentication required.",
                status=401,
                mimetype="text/plain",
                headers={
                    "WWW-Authenticate": 'Basic realm="Relationship Intelligence", charset="UTF-8"',
                    "Cache-Control": "no-store",
                },
            )
        return None

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; base-uri 'self'; frame-ancestors 'none'")
        if request.path.startswith("/api/") or request.path.startswith("/brief/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(DataError)
    def data_error(error):
        return jsonify(error=str(error)), 404 if "No customer" in str(error) else 409

    @app.errorhandler(OSError)
    def source_error(error):
        app.logger.error("Backend source is unavailable.")
        return jsonify(error="The relationship snapshot is temporarily unavailable. Please try again."), 503

    @app.get("/")
    def index():
        return render_template("index.html", bank_name=bank.bank_name)

    @app.get("/api/customers")
    def customers():
        return jsonify(bank.customers())

    @app.get("/api/customer/<cif>")
    def customer(cif):
        return jsonify(bank.dashboard(cif))

    @app.post("/api/customer/<cif>/recommendations")
    def recommend(cif):
        # This local UI has no upload/write endpoints; this POST triggers optional AI work.
        origin = request.headers.get("Origin")
        if origin and urlsplit(origin).netloc != request.host:
            return jsonify(error="This request must come from the relationship dashboard."), 403
        if not request.is_json or request.headers.get("X-Requested-With") != "RelationshipDashboard":
            return jsonify(error="Invalid dashboard request."), 400
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            return jsonify(error="Invalid request body."), 400
        result = bank.recommend(cif, version=body.get("version"), force=body.get("refresh") is True)
        return jsonify(result)

    @app.get("/brief/<cif>")
    def brief(cif):
        data = bank.dashboard(cif)
        response = Response(render_template("brief.html", position_chart=position_svg(data["profile"]), bank_logo_data=logo_data_uri(), **data), mimetype="text/html")
        if request.args.get("download") == "1":
            response.headers["Content-Disposition"] = f'attachment; filename="visit_brief_{data["profile"]["cif"]}_{data["profile"]["reporting_month"]}.html"'
        return response

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    return app


# Vercel's Python runtime detects this top-level WSGI application. Local
# Windows startup continues to use run.py/Waitress through create_app().
app = create_app()


if __name__ == "__main__":
    from run import main
    main()
