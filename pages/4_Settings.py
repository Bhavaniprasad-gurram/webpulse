from pathlib import Path
import streamlit as st
from config import config
from database.connection import get_db, test_connection
from database.models import Website, MonitoringResult, Incident, AlertHistory
from services.alert_service import AlertService
from components.sidebar import render_sidebar

# Page Configuration
st.set_page_config(page_title="Settings — WebPulse", layout="wide")

# Load CSS
css_path = Path(__file__).resolve().parent.parent / "static" / "styles.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

render_sidebar()

st.title("Settings")
st.caption("Check intervals, email alerts and database connection.")

# ----------------------------------------------------
# 1. Monitoring settings
# ----------------------------------------------------
st.subheader("Monitoring settings")
st.markdown("Defaults used when a website is added without its own values.")

c1, c2 = st.columns(2)
with c1:
    st.text_input("Default check interval (seconds)", value=str(config.DEFAULT_INTERVAL_SECONDS), disabled=True)
    st.caption("How often new websites are checked (change it in `.env`).")

    st.text_input("Failures before an incident opens", value=str(config.FAILURE_THRESHOLD), disabled=True)
    st.caption("How many failed checks in a row open an incident.")

with c2:
    st.text_input("Default request timeout (seconds)", value=str(config.DEFAULT_TIMEOUT_SECONDS), disabled=True)
    st.caption("How long a check waits for an answer before it fails.")

    st.text_input("Slow response limit (ms)", value=str(config.SLOW_RESPONSE_THRESHOLD_MS), disabled=True)
    st.caption("Responses slower than this are shown as Degraded.")

st.markdown("<div class='wp-section-header'></div>", unsafe_allow_html=True)

# ----------------------------------------------------
# 2. Email alerts
# ----------------------------------------------------
st.subheader("Email alerts (SMTP)")

smtp_active = AlertService.is_configured()
if smtp_active:
    st.success(f"Email alerts are on, sending through `{config.SMTP_HOST}:{config.SMTP_PORT}`.")
else:
    st.warning(
        "**Email alerts are off**: outages are still tracked here, "
        "but no emails are sent. To turn them on, add SMTP details in your `.env` file."
    )

with st.expander("Show SMTP settings", expanded=False):
    s_col1, s_col2 = st.columns(2)
    with s_col1:
        st.write(f"**Enabled:** `{config.SMTP_ENABLED}`")
        st.write(f"**Host:** `{config.SMTP_HOST}`")
        st.write(f"**Port:** `{config.SMTP_PORT}`")
    with s_col2:
        st.write(f"**Sender:** `{config.SMTP_SENDER}`")
        st.write(f"**Alert Recipient:** `{config.ALERT_RECIPIENT or 'Not set'}`")
        st.write(f"**Auth User:** `{'Configured' if config.SMTP_USER else 'None'}`")

st.markdown("<div class='wp-section-header'></div>", unsafe_allow_html=True)

# ----------------------------------------------------
# 3. Database
# ----------------------------------------------------
st.subheader("Database")

col_d1, col_d2 = st.columns([3, 2])

with col_d1:
    db_ok, db_msg = test_connection()
    if db_ok:
        st.markdown(
            """
            <div style="background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 8px; padding: 0.9rem; color: #065f46; font-size: 0.9rem;">
                <strong>Database connected</strong>.
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
    if st.button("Test database connection", use_container_width=True):
        ok, res = test_connection()
        if ok:
            st.success("Database connection works.")
        else:
            st.error(f"Database connection failed: {res}")

with col_d2:
    with get_db() as session:
        site_cnt = session.query(Website).count()
        results_cnt = session.query(MonitoringResult).count()
        inc_cnt = session.query(Incident).count()
        alert_cnt = session.query(AlertHistory).count()

    st.markdown(
        f"""
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 0.9rem; font-size: 0.85rem;">
            <strong>Records in the database:</strong><br>
            Websites: <code>{site_cnt}</code><br>
            Checks: <code>{results_cnt}</code><br>
            Incidents: <code>{inc_cnt}</code><br>
            Alerts: <code>{alert_cnt}</code>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div class='wp-section-header'></div>", unsafe_allow_html=True)

# ----------------------------------------------------
# 4. Background worker
# ----------------------------------------------------
st.subheader("Background worker")
st.markdown(
    """
    WebPulse runs as two parts:
    - **This app (Streamlit)**: the dashboard — add websites, run checks and see results.
    - **Background worker (APScheduler)**: a separate process that checks the websites on schedule and writes the results to the database.
    
    To start the worker, open a second terminal and run:
    ```bash
    python -m workers.monitor_worker
    ```
    """
)
