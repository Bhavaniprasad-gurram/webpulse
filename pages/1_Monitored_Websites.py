from pathlib import Path
from datetime import datetime, timezone
import streamlit as st
import pandas as pd

# Page Configuration
st.set_page_config(page_title="Monitored Websites — WebPulse", page_icon="🌐", layout="wide")

# Load CSS
css_path = Path(__file__).resolve().parent.parent / "static" / "styles.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

from config import config
from database.connection import get_db
from database.models import Website, MonitoringResult
from repositories.website_repository import WebsiteRepository
from repositories.monitoring_repository import MonitoringRepository
from services.website_service import WebsiteService, ValidationError
from services.monitoring_service import MonitoringService
from components.sidebar import render_sidebar
from components.status_badges import render_badge

render_sidebar()

st.title("Monitored Websites")
st.caption("Register endpoints, adjust polling frequencies, trigger immediate checks, or edit target configurations.")

# ----------------------------------------------------
# 1. Registration Section
# ----------------------------------------------------
with st.expander("➕ Register New Website Target", expanded=False):
    st.markdown("Register a web application or API endpoint to begin automated availability and latency tracking.")
    
    with st.form("form_register_website", clear_on_submit=True):
        col_name, col_url = st.columns([1, 2])
        with col_name:
            site_name = st.text_input("Website Name", placeholder="e.g. Production API Gateway")
        with col_url:
            site_url = st.text_input("Target URL (HTTP/HTTPS)", placeholder="https://api.example.com/health")

        col_int, col_to = st.columns(2)
        with col_int:
            interval = st.number_input(
                "Monitoring Interval (seconds)",
                min_value=10,
                max_value=86400,
                value=config.DEFAULT_INTERVAL_SECONDS,
                help="How frequently the background worker checks this endpoint (10s to 86,400s).",
            )
        with col_to:
            timeout = st.number_input(
                "Request Timeout (seconds)",
                min_value=1,
                max_value=60,
                value=config.DEFAULT_TIMEOUT_SECONDS,
                help="Duration before an unanswered HTTP request is declared a CONNECTION_TIMEOUT.",
            )

        description = st.text_area("Description (Optional)", placeholder="Core customer payment service endpoint.")
        submit = st.form_submit_button("Register Target", type="primary")

        if submit:
            try:
                new_site = WebsiteService.register_website(
                    name=site_name,
                    url=site_url,
                    interval=int(interval),
                    timeout=int(timeout),
                    description=description,
                )
                st.success(f"Target '{new_site.name}' registered successfully! Triggering initial availability test...")
                # Immediate initial check so it doesn't stay pending
                MonitoringService.record_and_evaluate(new_site.id)
                st.rerun()
            except ValidationError as val_err:
                st.error(f"Validation Error: {str(val_err)}")
            except Exception as e:
                st.error(f"Failed to register website: {str(e)}")

st.markdown("<div class='wp-section-header'></div>", unsafe_allow_html=True)

# ----------------------------------------------------
# 2. Existing Websites Management List
# ----------------------------------------------------
st.subheader("Configured Targets")

with get_db() as session:
    all_websites = WebsiteRepository.get_all(session, include_inactive=True)

if not all_websites:
    st.info("No websites currently registered. Use the registration form above to add your first target.")
else:
    for site in all_websites:
        with st.container():
            with get_db() as session:
                latest = WebsiteRepository.get_latest_result(session, site.id)

            # Determine Status
            if not site.is_active:
                status_label = "Paused"
            elif not latest:
                status_label = "Pending"
            elif not latest.is_available:
                status_label = "Down"
            elif latest.response_time_ms and latest.response_time_ms >= config.SLOW_RESPONSE_THRESHOLD_MS:
                status_label = "Degraded"
            else:
                status_label = "Operational"

            # Row Header
            col_main, col_badge, col_btn_check = st.columns([5, 2, 2])
            with col_main:
                st.markdown(f"### {site.name}")
                st.markdown(f"🔗 `{site.url}`")
                if site.description:
                    st.caption(site.description)
            with col_badge:
                st.markdown(render_badge(status_label), unsafe_allow_html=True)
                st.caption(f"Interval: {site.monitoring_interval_seconds}s | Timeout: {site.timeout_seconds}s")
            with col_btn_check:
                if st.button("⚡ Test Check Now", key=f"site_check_{site.id}", use_container_width=True):
                    with st.spinner("Checking target..."):
                        chk = MonitoringService.record_and_evaluate(site.id)
                        if chk and chk.is_available:
                            st.success(f"Operational ({chk.response_time_ms}ms, HTTP {chk.http_status_code})")
                        elif chk:
                            st.error(f"Unavailable ({chk.error_type or 'Failed'})")
                        st.rerun()

            # Website Actions & History in Sub-Tabs
            tab_history, tab_edit, tab_delete = st.tabs(["📊 Check History", "⚙️ Edit Settings", "🗑️ Remove Target"])

            with tab_history:
                with get_db() as session:
                    recent_checks = MonitoringRepository.get_recent_by_website(session, site.id, limit=15)
                
                if not recent_checks:
                    st.write("No historical checks recorded yet. Click 'Test Check Now' above to perform first check.")
                else:
                    data = []
                    for rc in recent_checks:
                        data.append({
                            "Timestamp (UTC)": rc.checked_at.strftime("%Y-%m-%d %H:%M:%S"),
                            "Result": "UP" if rc.is_available else "DOWN",
                            "HTTP Code": rc.http_status_code or "--",
                            "Latency (ms)": rc.response_time_ms if rc.response_time_ms is not None else "--",
                            "Error / Note": rc.error_message or rc.error_type or "OK",
                        })
                    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

            with tab_edit:
                with st.form(f"form_edit_{site.id}"):
                    e_name = st.text_input("Target Name", value=site.name)
                    e_url = st.text_input("Target URL", value=site.url)
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        e_interval = st.number_input("Interval (seconds)", min_value=10, max_value=86400, value=site.monitoring_interval_seconds)
                    with col_e2:
                        e_timeout = st.number_input("Timeout (seconds)", min_value=1, max_value=60, value=site.timeout_seconds)
                    e_active = st.checkbox("Active (Monitoring Enabled)", value=site.is_active)
                    e_desc = st.text_area("Description", value=site.description or "")

                    if st.form_submit_button("Save Changes"):
                        try:
                            WebsiteService.update_website(
                                website_id=site.id,
                                name=e_name,
                                url=e_url,
                                interval=int(e_interval),
                                timeout=int(e_timeout),
                                is_active=e_active,
                                description=e_desc,
                            )
                            st.success("Target updated successfully!")
                            st.rerun()
                        except ValidationError as err:
                            st.error(str(err))
                        except Exception as e:
                            st.error(f"Error updating target: {e}")

            with tab_delete:
                st.warning("⚠️ **Warning**: Deleting this website will permanently remove its entire monitoring history and incident logs.")
                confirm = st.checkbox(f"Yes, permanently delete '{site.name}'", key=f"del_confirm_{site.id}")
                if st.button("Delete Target", key=f"del_btn_{site.id}", type="primary", disabled=not confirm):
                    WebsiteService.delete_website(site.id)
                    st.success(f"Website '{site.name}' removed.")
                    st.rerun()

            st.divider()
