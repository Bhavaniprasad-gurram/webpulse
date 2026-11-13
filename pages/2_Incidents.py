from pathlib import Path
from datetime import datetime, timezone
import streamlit as st
import pandas as pd

# Page Configuration
st.set_page_config(page_title="Incidents & Outages — WebPulse", page_icon="🚨", layout="wide")

# Load CSS
css_path = Path(__file__).resolve().parent.parent / "static" / "styles.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

from database.connection import get_db
from database.models import Incident, AlertHistory, Website
from repositories.incident_repository import IncidentRepository
from repositories.website_repository import WebsiteRepository
from components.sidebar import render_sidebar
from components.status_badges import render_badge

render_sidebar()

st.title("Downtime Incidents & Outage Telemetry")
st.caption(
    "Automated incident tracking initiated when consecutive check failures exceed the configured threshold. "
    "Incidents are automatically marked resolved once the website returns to an operational state."
)

col_r1, col_r2 = st.columns([4, 1])
with col_r2:
    if st.button("🔄 Refresh Incidents", use_container_width=True):
        st.rerun()

# ----------------------------------------------------
# 1. Active Outages (Open Incidents)
# ----------------------------------------------------
st.subheader("Active Incidents (Unresolved Outages)")

with get_db() as session:
    open_incidents = (
        session.query(Incident)
        .filter(Incident.status == "OPEN")
        .order_by(Incident.started_at.desc())
        .all()
    )

if not open_incidents:
    st.success("✅ **All Systems Operational**: There are currently no active downtime incidents across any monitored website.")
else:
    for inc in open_incidents:
        with get_db() as session:
            site = WebsiteRepository.get_by_id(session, inc.website_id)
            site_name = site.name if site else f"Website #{inc.website_id}"
            site_url = site.url if site else "N/A"

        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        elapsed_secs = max(0, int((now_utc - inc.started_at).total_seconds()))
        mins, secs = divmod(elapsed_secs, 60)
        hours, mins = divmod(mins, 60)
        duration_str = f"{hours}h {mins}m {secs}s" if hours > 0 else f"{mins}m {secs}s"

        with st.container():
            st.markdown(
                f"""
                <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 0.8rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700; color: #991b1b; font-size: 1.05rem;">🚨 Outage: {site_name}</span>
                        <span class="wp-badge wp-badge-down">OPEN INCIDENT #{inc.id}</span>
                    </div>
                    <div style="font-size: 0.85rem; color: #7f1d1d; margin-top: 0.35rem;">
                        Target: <code>{site_url}</code> | Started: {inc.started_at.strftime('%Y-%m-%d %H:%M:%S UTC')} | 
                        <strong>Active Duration: {duration_str}</strong>
                    </div>
                    <div style="font-size: 0.82rem; color: #450a0a; margin-top: 0.3rem;">
                        <strong>Root Cause:</strong> {inc.cause_summary or 'Service unavailable / network timeout'}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

st.markdown("<div class='wp-section-header'></div>", unsafe_allow_html=True)

# ----------------------------------------------------
# 2. Historical Resolved Incidents
# ----------------------------------------------------
st.subheader("Incident History")

with get_db() as session:
    all_websites = WebsiteRepository.get_all(session, include_inactive=True)

website_options = {"All Websites": None}
for w in all_websites:
    website_options[w.name] = w.id

filter_site = st.selectbox("Filter by Monitored Target", options=list(website_options.keys()))
selected_site_id = website_options[filter_site]

with get_db() as session:
    query = session.query(Incident)
    if selected_site_id:
        query = query.filter(Incident.website_id == selected_site_id)
    history_incidents = query.order_by(Incident.started_at.desc()).limit(100).all()

if not history_incidents:
    st.info("No incident records found matching the selected filter.")
else:
    table_data = []
    for inc in history_incidents:
        with get_db() as session:
            site = WebsiteRepository.get_by_id(session, inc.website_id)
            site_name = site.name if site else f"Site #{inc.website_id}"

        if inc.status == "OPEN":
            status_col = "🚨 OPEN"
            dur_display = "Active Outage"
        else:
            status_col = "✅ RESOLVED"
            if inc.duration_seconds is not None:
                m, s = divmod(inc.duration_seconds, 60)
                h, m = divmod(m, 60)
                dur_display = f"{h}h {m}m {s}s" if h > 0 else f"{m}m {s}s"
            else:
                dur_display = "--"

        table_data.append({
            "ID": f"#{inc.id}",
            "Website": site_name,
            "Status": status_col,
            "Started At (UTC)": inc.started_at.strftime("%Y-%m-%d %H:%M:%S"),
            "Resolved At (UTC)": inc.resolved_at.strftime("%Y-%m-%d %H:%M:%S") if inc.resolved_at else "In Progress",
            "Downtime Duration": dur_display,
            "Root Cause": inc.cause_summary or "--",
        })

    st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

st.markdown("<div class='wp-section-header'></div>", unsafe_allow_html=True)

# ----------------------------------------------------
# 3. Alert Notification Dispatch Audit Log
# ----------------------------------------------------
st.subheader("Alert Notification Dispatch Log")
st.caption("Audit trail of automated email alert attempts for downtime and recovery events.")

with get_db() as session:
    alerts = IncidentRepository.get_alert_logs(session, limit=50)

if not alerts:
    st.info("No alert dispatch logs recorded yet.")
else:
    alert_records = []
    for a in alerts:
        with get_db() as session:
            site = WebsiteRepository.get_by_id(session, a.website_id)
            site_name = site.name if site else f"Site #{a.website_id}"

        alert_records.append({
            "Timestamp (UTC)": a.sent_at.strftime("%Y-%m-%d %H:%M:%S") if a.sent_at else "--",
            "Website": site_name,
            "Event": a.alert_type,
            "Delivery Status": a.delivery_status,
            "Recipient": a.recipient or "--",
            "Details / Error": a.error_message or "Successfully dispatched",
        })

    st.dataframe(pd.DataFrame(alert_records), use_container_width=True, hide_index=True)
