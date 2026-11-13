from pathlib import Path
import streamlit as st
from config import config
from database.connection import get_db, test_connection
from database.models import Website, MonitoringResult, Incident, AlertHistory
from services.alert_service import AlertService
from components.sidebar import render_sidebar

# Page Configuration
st.set_page_config(page_title="Platform Settings — WebPulse", page_icon="⚙️", layout="wide")

# Load CSS
css_path = Path(__file__).resolve().parent.parent / "static" / "styles.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

render_sidebar()

st.title("System & Monitoring Settings")
st.caption("Manage global observability thresholds, email notification channels, and database connection diagnostics.")

# ----------------------------------------------------
# 1. Global Monitoring Thresholds
# ----------------------------------------------------
st.subheader("Observability Parameters & Thresholds")
st.markdown("Global default parameters used when targets are registered without specific overrides.")

c1, c2 = st.columns(2)
with c1:
    st.text_input("Default Polling Interval (seconds)", value=str(config.DEFAULT_INTERVAL_SECONDS), disabled=True)
    st.caption("Global polling frequency for newly registered endpoints (configurable via `.env`).")

    st.text_input("Failure Threshold (consecutive failed checks)", value=str(config.FAILURE_THRESHOLD), disabled=True)
    st.caption("Number of consecutive failed HTTP checks required before transitioning to an OPEN incident.")

with c2:
    st.text_input("Default Request Timeout (seconds)", value=str(config.DEFAULT_TIMEOUT_SECONDS), disabled=True)
    st.caption("Maximum duration permitted before requests abort with CONNECTION_TIMEOUT.")

    st.text_input("Slow Response Latency Warning (ms)", value=str(config.SLOW_RESPONSE_THRESHOLD_MS), disabled=True)
    st.caption("Threshold in milliseconds above which operational targets are flagged as 'Degraded'.")

st.markdown("<div class='wp-section-header'></div>", unsafe_allow_html=True)

# ----------------------------------------------------
# 2. Email Alerts (SMTP) Configuration Status
# ----------------------------------------------------
st.subheader("Email Alert Channel (SMTP)")

smtp_active = AlertService.is_configured()
if smtp_active:
    st.success(f"✅ **Email Alerts Operational**: Notifications enabled via `{config.SMTP_HOST}:{config.SMTP_PORT}`.")
else:
    st.warning(
        "⚠️ **Email Alerts Not Configured / Disabled**: Outages are tracked in the database and UI, "
        "but outbound email notifications are disabled. To enable, configure SMTP credentials in your `.env` file."
    )

with st.expander("Inspect Current SMTP Settings", expanded=False):
    s_col1, s_col2 = st.columns(2)
    with s_col1:
        st.write(f"**SMTP Enabled:** `{config.SMTP_ENABLED}`")
        st.write(f"**Host:** `{config.SMTP_HOST}`")
        st.write(f"**Port:** `{config.SMTP_PORT}`")
    with s_col2:
        st.write(f"**Sender Identity:** `{config.SMTP_SENDER}`")
        st.write(f"**Alert Recipient:** `{config.ALERT_RECIPIENT or 'Not set'}`")
        st.write(f"**Auth User:** `{'Configured' if config.SMTP_USER else 'None'}`")

st.markdown("<div class='wp-section-header'></div>", unsafe_allow_html=True)

# ----------------------------------------------------
# 3. Database Diagnostics & System Telemetry
# ----------------------------------------------------
st.subheader("Database Diagnostics")

col_d1, col_d2 = st.columns([3, 2])

with col_d1:
    db_ok, db_msg = test_connection()
    if db_ok:
        st.markdown(
            """
            <div style="background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 8px; padding: 0.9rem; color: #065f46; font-size: 0.9rem;">
                <strong>Database Connected</strong>: Connection pool is active and operational.
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 0.9rem; color: #991b1b; font-size: 0.9rem;">
                <strong>Connection Error:</strong> {db_msg}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Test DB Connection Button
    if st.button("🧪 Test Database Connectivity", use_container_width=True):
        ok, res = test_connection()
        if ok:
            st.success("Database ping test succeeded (SELECT 1).")
        else:
            st.error(f"Database ping test failed: {res}")

with col_d2:
    with get_db() as session:
        site_cnt = session.query(Website).count()
        results_cnt = session.query(MonitoringResult).count()
        inc_cnt = session.query(Incident).count()
        alert_cnt = session.query(AlertHistory).count()

    st.markdown(
        f"""
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 0.9rem; font-size: 0.85rem;">
            <strong>Table Record Counts:</strong><br>
            • Registered Websites: <code>{site_cnt}</code><br>
            • Monitoring Check Results: <code>{results_cnt}</code><br>
            • Downtime Incidents: <code>{inc_cnt}</code><br>
            • Alert Logs: <code>{alert_cnt}</code>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div class='wp-section-header'></div>", unsafe_allow_html=True)

# ----------------------------------------------------
# 4. Background Worker Architecture
# ----------------------------------------------------
st.subheader("Background Monitoring Worker Architecture")
st.markdown(
    """
    WebPulse operates using a decoupled architecture:
    - **Streamlit Web UI**: Responsible for interactive observability, registration, manual testing, and analytics.
    - **Independent APScheduler Worker**: Operates in a separate background Python process, continuously querying the database and polling registered targets without UI latency.
    
    To start the background worker locally, open a separate terminal and execute:
    ```bash
    python -m workers.monitor_worker
    ```
    """
)
