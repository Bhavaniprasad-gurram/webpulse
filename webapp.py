"""
WebPulse — Flask Web Application
A website monitoring dashboard replacing the previous Streamlit frontend.
Reuses the existing backend (database, services, repositories).
"""

import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, abort
)

# ---------------------------------------------------------------------------
# Backend imports
# ---------------------------------------------------------------------------
from config import config
from database.connection import get_db, test_connection
from database.init_db import init_database
from database.models import Website, MonitoringResult, Incident, AlertHistory

from repositories.website_repository import WebsiteRepository
from repositories.monitoring_repository import MonitoringRepository
from repositories.incident_repository import IncidentRepository

from services.website_service import WebsiteService, ValidationError
from services.monitoring_service import MonitoringService
from services.analytics_service import AnalyticsService
from services.alert_service import AlertService

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "webpulse-secret-key-prod-2026")

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def compute_status(site: Website, latest: Optional[MonitoringResult]) -> str:
    """Determine standardized uppercase status string."""
    if not site.is_active:
        return "PAUSED"
    if not latest:
        return "PENDING"
    if not latest.is_available:
        return "DOWN"
    if latest.response_time_ms and latest.response_time_ms >= config.SLOW_RESPONSE_THRESHOLD_MS:
        return "DEGRADED"
    return "OPERATIONAL"


def format_duration(seconds: Optional[int]) -> str:
    """Format duration in seconds into human-readable string."""
    if seconds is None:
        return "Ongoing"
    secs = max(0, int(seconds))
    mins, s = divmod(secs, 60)
    hours, m = divmod(mins, 60)
    if hours > 0:
        return f"{hours}h {m}m"
    if mins > 0:
        return f"{mins}m {s}s"
    return f"{s}s"


# ---------------------------------------------------------------------------
# Jinja2 custom filters & context processor
# ---------------------------------------------------------------------------

@app.template_filter("datefmt")
def datefmt_filter(value, fmt="%Y-%m-%d %H:%M:%S"):
    """Format a datetime object for display."""
    if value is None:
        return "—"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return value
    return value.strftime(fmt)


@app.template_filter("duration")
def duration_filter(value):
    """Render seconds as human-friendly duration."""
    return format_duration(value)


@app.template_filter("ms_fmt")
def ms_fmt_filter(value):
    """Format a millisecond value."""
    if value is None:
        return "—"
    try:
        return f"{float(value):.1f} ms"
    except (TypeError, ValueError):
        return str(value)


@app.context_processor
def inject_globals():
    try:
        db_ok, _ = test_connection()
    except Exception:
        db_ok = False
    return {
        "now": datetime.now(timezone.utc),
        "app_name": "WebPulse",
        "db_connected": db_ok,
    }


# ---------------------------------------------------------------------------
# Route: Dashboard
# ---------------------------------------------------------------------------

@app.route("/")
def dashboard():
    """Overview dashboard with KPIs, fleet status table, and recent incidents."""
    with get_db() as session:
        try:
            kpis = AnalyticsService.get_overall_system_kpis()
        except Exception:
            kpis = {
                "total_websites": 0,
                "operational_count": 0,
                "down_count": 0,
                "degraded_count": 0,
                "pending_count": 0,
                "overall_uptime_24h": None,
                "avg_response_time_ms": None,
                "active_incidents": 0,
            }

        all_websites = WebsiteRepository.get_all(session, include_inactive=True)
        yesterday = AnalyticsService.get_time_window("24h")
        websites_data = []

        for site in all_websites:
            latest = WebsiteRepository.get_latest_result(session, site.id)
            uptime_data = AnalyticsService.calculate_website_uptime(site.id, start_time=yesterday)
            status_str = compute_status(site, latest)

            websites_data.append({
                "id": site.id,
                "name": site.name,
                "url": site.url,
                "status": status_str,
                "latency_ms": latest.response_time_ms if latest else None,
                "http_code": latest.http_status_code if latest else None,
                "uptime_24h": uptime_data["uptime_pct"],
                "last_checked": latest.checked_at if latest else None,
            })

        # Recent incidents (last 10)
        recent_inc = IncidentRepository.get_all(session, website_id=None, status=None, limit=10)
        recent_data = []
        for inc in recent_inc:
            site = WebsiteRepository.get_by_id(session, inc.website_id)
            recent_data.append({
                "id": inc.id,
                "website_name": site.name if site else f"Site #{inc.website_id}",
                "status": inc.status,
                "started_at": inc.started_at,
                "resolved_at": inc.resolved_at,
                "duration_seconds": inc.duration_seconds,
                "cause_summary": inc.cause_summary,
            })

    return render_template(
        "dashboard.html",
        kpis=kpis,
        websites=websites_data,
        recent_incidents=recent_data,
    )


# ---------------------------------------------------------------------------
# Routes: Websites
# ---------------------------------------------------------------------------

@app.route("/websites")
def website_list():
    """List all monitored websites with card view and registration modal."""
    with get_db() as session:
        websites = WebsiteRepository.get_all(session, include_inactive=True)
        yesterday = AnalyticsService.get_time_window("24h")
        items = []
        for site in websites:
            latest = WebsiteRepository.get_latest_result(session, site.id)
            uptime_data = AnalyticsService.calculate_website_uptime(site.id, start_time=yesterday)
            items.append({
                "id": site.id,
                "name": site.name,
                "url": site.url,
                "description": site.description,
                "interval": site.monitoring_interval_seconds,
                "timeout": site.timeout_seconds,
                "is_active": site.is_active,
                "status": compute_status(site, latest),
                "latency_ms": latest.response_time_ms if latest else None,
                "http_code": latest.http_status_code if latest else None,
                "uptime_24h": uptime_data["uptime_pct"],
                "last_checked": latest.checked_at if latest else None,
            })

    return render_template("websites.html", websites=items)


@app.route("/websites", methods=["POST"])
def website_add():
    """Register a new website from modal form submission."""
    name = request.form.get("name", "").strip()
    url = request.form.get("url", "").strip()
    interval = int(request.form.get("interval", config.DEFAULT_INTERVAL_SECONDS))
    timeout = int(request.form.get("timeout", config.DEFAULT_TIMEOUT_SECONDS))
    description = request.form.get("description", "").strip()

    try:
        new_site = WebsiteService.register_website(
            name=name,
            url=url,
            interval=interval,
            timeout=timeout,
            description=description or None,
        )
        # Perform immediate health check
        MonitoringService.record_and_evaluate(new_site.id)
        flash(f"Website '{new_site.name}' added successfully.", "success")
    except ValidationError as exc:
        flash(f"Validation error: {exc}", "danger")
    except Exception as exc:
        flash(f"Error adding website: {exc}", "danger")

    return redirect(url_for("website_list"))


@app.route("/websites/<int:website_id>/edit")
def website_edit_form(website_id):
    """Render edit form for a website."""
    with get_db() as session:
        site = WebsiteRepository.get_by_id(session, website_id)
        if not site:
            abort(404)

        site_dict = {
            "id": site.id,
            "name": site.name,
            "url": site.url,
            "interval": site.monitoring_interval_seconds,
            "timeout": site.timeout_seconds,
            "description": site.description or "",
            "is_active": site.is_active,
        }

    return render_template("website_edit.html", website=site_dict)


@app.route("/websites/<int:website_id>/edit", methods=["POST"])
def website_edit_save(website_id):
    """Save updates to a website."""
    name = request.form.get("name", "").strip()
    url = request.form.get("url", "").strip()
    interval = int(request.form.get("interval", config.DEFAULT_INTERVAL_SECONDS))
    timeout = int(request.form.get("timeout", config.DEFAULT_TIMEOUT_SECONDS))
    is_active = request.form.get("is_active") in ("1", "on", "true")
    description = request.form.get("description", "").strip()

    try:
        WebsiteService.update_website(
            website_id=website_id,
            name=name,
            url=url,
            interval=interval,
            timeout=timeout,
            is_active=is_active,
            description=description or None,
        )
        flash("Website settings updated successfully.", "success")
    except ValidationError as exc:
        flash(f"Validation error: {exc}", "danger")
    except Exception as exc:
        flash(f"Error updating website: {exc}", "danger")

    return redirect(url_for("website_list"))


@app.route("/websites/<int:website_id>/delete", methods=["POST"])
def website_delete(website_id):
    """Delete a monitored website."""
    try:
        WebsiteService.delete_website(website_id)
        flash("Website removed.", "success")
    except Exception as exc:
        flash(f"Error removing website: {exc}", "danger")

    return redirect(url_for("website_list"))


@app.route("/websites/<int:website_id>/check", methods=["POST"])
def website_check(website_id):
    """Trigger an immediate manual check for a website."""
    try:
        result = MonitoringService.record_and_evaluate(website_id)
        if result and result.is_available:
            flash(f"Health check passed: Operational ({result.response_time_ms} ms, HTTP {result.http_status_code}).", "success")
        elif result:
            flash(f"Health check failed: {result.error_type or 'Service Down'}.", "danger")
        else:
            flash("Check could not be performed.", "warning")
    except Exception as exc:
        flash(f"Error running check: {exc}", "danger")

    return redirect(request.referrer or url_for("dashboard"))


# ---------------------------------------------------------------------------
# Route: Incidents
# ---------------------------------------------------------------------------

@app.route("/incidents")
def incidents():
    """Incidents page with active outages and filterable history."""
    website_id_param = request.args.get("website_id", type=int)

    with get_db() as session:
        all_sites = WebsiteRepository.get_all(session, include_inactive=True)

        # Open incidents
        open_raw = IncidentRepository.get_all(session, website_id=website_id_param, status="OPEN", limit=50)
        open_incidents = []
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        for inc in open_raw:
            site = WebsiteRepository.get_by_id(session, inc.website_id)
            elapsed = int((now_utc - inc.started_at).total_seconds()) if inc.started_at else 0
            open_incidents.append({
                "id": inc.id,
                "website_name": site.name if site else f"Site #{inc.website_id}",
                "website_url": site.url if site else "",
                "started_at": inc.started_at,
                "duration_str": format_duration(elapsed),
                "cause_summary": inc.cause_summary,
            })

        # Incident history (all statuses)
        history_raw = IncidentRepository.get_all(session, website_id=website_id_param, status=None, limit=100)
        history = []
        for inc in history_raw:
            site = WebsiteRepository.get_by_id(session, inc.website_id)
            history.append({
                "id": inc.id,
                "website_name": site.name if site else f"Site #{inc.website_id}",
                "status": inc.status,
                "started_at": inc.started_at,
                "resolved_at": inc.resolved_at,
                "duration_str": format_duration(inc.duration_seconds),
                "cause_summary": inc.cause_summary,
            })

    return render_template(
        "incidents.html",
        open_incidents=open_incidents,
        history=history,
        websites=all_sites,
    )


# ---------------------------------------------------------------------------
# Route: Analytics
# ---------------------------------------------------------------------------

@app.route("/analytics")
def analytics():
    """Analytics overview page with stats cards and charts."""
    period = request.args.get("period", "24h")
    website_id = request.args.get("website_id", type=int)

    start_time = AnalyticsService.get_time_window(period)

    with get_db() as session:
        all_sites = WebsiteRepository.get_all(session, include_inactive=True)

    stats = AnalyticsService.calculate_response_time_stats(website_id=website_id, start_time=start_time)

    return render_template(
        "analytics.html",
        stats=stats,
        period=period,
        websites=all_sites,
        selected_website_id=website_id,
    )


# ---------------------------------------------------------------------------
# JSON APIs for Charts
# ---------------------------------------------------------------------------

@app.route("/api/latency-data")
def api_latency_data():
    """Return latency data JSON for Chart.js line chart."""
    period = request.args.get("period", "24h")
    website_id = request.args.get("website_id", type=int)

    hours_map = {"24h": 24, "7d": 168, "30d": 720}
    hours = hours_map.get(period, 24)

    try:
        df = AnalyticsService.get_latency_timeseries(website_id=website_id, hours=hours)
        if df is None or df.empty:
            return jsonify({"labels": [], "values": [], "threshold": config.SLOW_RESPONSE_THRESHOLD_MS})

        labels = [dt.strftime("%b %d %H:%M") for dt in df["checked_at"]]
        values = [round(v, 1) if v is not None else None for v in df["response_time_ms"]]

        return jsonify({
            "labels": labels,
            "values": values,
            "threshold": config.SLOW_RESPONSE_THRESHOLD_MS,
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/uptime-data")
def api_uptime_data():
    """Return uptime comparison data JSON for Chart.js bar chart."""
    period = request.args.get("period", "24h")

    try:
        df = AnalyticsService.get_website_comparison(period=period)
        if df is None or df.empty:
            return jsonify({"labels": [], "values": []})

        labels = df["name"].tolist()
        values = [round(v, 2) if v is not None else 0 for v in df["uptime_pct"]]

        return jsonify({
            "labels": labels,
            "values": values,
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Route: Settings
# ---------------------------------------------------------------------------

@app.route("/settings")
def settings():
    """Settings page — threshold parameters, SMTP status, and DB telemetry."""
    db_ok, db_msg = test_connection()

    # Wrapped config with expected template names
    cfg_display = {
        "DEFAULT_CHECK_INTERVAL": config.DEFAULT_INTERVAL_SECONDS,
        "DEFAULT_TIMEOUT": config.DEFAULT_TIMEOUT_SECONDS,
        "FAILURE_THRESHOLD": config.FAILURE_THRESHOLD,
        "SLOW_RESPONSE_MS": config.SLOW_RESPONSE_THRESHOLD_MS,
        "SMTP_HOST": config.SMTP_HOST,
        "SMTP_PORT": config.SMTP_PORT,
        "ALERT_SENDER": config.SMTP_SENDER,
        "ALERT_RECIPIENT": config.ALERT_RECIPIENT,
    }

    with get_db() as session:
        record_counts = {
            "websites": session.query(Website).count(),
            "results": session.query(MonitoringResult).count(),
            "incidents": session.query(Incident).count(),
            "alerts": session.query(AlertHistory).count(),
        }

    return render_template(
        "settings.html",
        config=cfg_display,
        smtp_configured=AlertService.is_configured(),
        db_status=(db_ok, db_msg),
        record_counts=record_counts,
    )


@app.route("/settings/test-db", methods=["POST"])
def test_db_connection():
    """Test database connectivity from UI."""
    db_ok, db_msg = test_connection()
    if db_ok:
        flash(f"Database connectivity test succeeded: {db_msg}", "success")
    else:
        flash(f"Database connectivity test failed: {db_msg}", "danger")
    return redirect(url_for("settings"))


# ---------------------------------------------------------------------------
# Error Handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def page_not_found(e):
    return render_template("error.html", code=404, message="The requested page could not be found."), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template("error.html", code=500, message="An internal server error occurred."), 500


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import logging
    # Quiet down static file 200/304 noise so terminal remains clean
    class StaticFilter(logging.Filter):
        def filter(self, record):
            msg = record.getMessage()
            return "/static/" not in msg and "/favicon.ico" not in msg

    logging.getLogger("werkzeug").addFilter(StaticFilter())

    init_database()

    print("\n" + "=" * 60)
    print("  🚀 WebPulse Dashboard is running!")
    print("  👉 URL: http://127.0.0.1:5000")
    print("  (Press CTRL+C in this terminal to stop)")
    print("=" * 60 + "\n")

    app.run(host="127.0.0.1", port=5000, debug=True)
