import os
from pathlib import Path
from datetime import datetime, timezone
import streamlit as st
import pandas as pd

# Page Configuration
st.set_page_config(
    page_title="WebPulse — Website Availability & Downtime Observability",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load Custom CSS Styling
css_path = Path(__file__).resolve().parent / "static" / "styles.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Imports
from config import config
from database.connection import test_connection, get_db
from database.models import Website, Incident
from repositories.website_repository import WebsiteRepository
from services.analytics_service import AnalyticsService
from services.monitoring_service import MonitoringService
from components.sidebar import render_sidebar
from components.metric_cards import render_metric_card
from components.status_badges import render_badge
from components.charts import render_latency_trend_chart, render_status_donut

# Render Sidebar
render_sidebar()

# Verify Database Connection
db_healthy, db_error = test_connection()
if not db_healthy:
    st.error(
        f"🚨 **Database Connectivity Issue**: Unable to connect to MySQL ({db_error}).\n\n"
        f"Please check your `.env` configuration and verify your database service is running."
    )
    st.stop()

# ----------------------------------------------------
# Top Hero Header Bar
# ----------------------------------------------------
col_title, col_actions = st.columns([4, 1.2])

with col_title:
    st.markdown(
        """
        <div class="wp-title-wrapper">
            <h1>Fleet Observability Overview</h1>
            <p>Live synthetic HTTP availability, latency trends, and automated outage incident tracking.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_actions:
    st.write("")
    if st.button("🔄 Sync Telemetry", use_container_width=True, type="primary"):
        st.rerun()

# ----------------------------------------------------
# 1. Premium KPI Metric Cards
# ----------------------------------------------------
kpis = AnalyticsService.get_overall_system_kpis()

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    render_metric_card(
        label="Monitored Fleet",
        value=str(kpis["total_websites"]),
        subtext="Active HTTP targets",
        accent="blue",
        icon="🌐"
    )
with c2:
    render_metric_card(
        label="Operational",
        value=str(kpis["operational_count"]),
        subtext="Passing all health checks",
        accent="emerald",
        icon="✅"
    )
with c3:
    render_metric_card(
        label="Active Outages",
        value=str(kpis["down_count"]),
        subtext=f"{kpis['active_incidents']} open incident(s)",
        accent="rose",
        icon="🚨"
    )
with c4:
    uptime_val = f"{kpis['overall_uptime_24h']}%" if kpis["overall_uptime_24h"] is not None else "No data"
    render_metric_card(
        label="Fleet Uptime (24h)",
        value=uptime_val,
        subtext="Weighted availability",
        accent="indigo",
        icon="📈"
    )
with c5:
    latency_val = f"{kpis['avg_response_time_ms']} ms" if kpis["avg_response_time_ms"] is not None else "--"
    render_metric_card(
        label="Avg Latency",
        value=latency_val,
        subtext="Rolling 24h average",
        accent="amber",
        icon="⚡"
    )

st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

# ----------------------------------------------------
# 2. Charts & Monitoring Overview
# ----------------------------------------------------
col_chart_left, col_chart_right = st.columns([6.8, 3.2])

with col_chart_left:
    st.markdown(
        """
        <div class="wp-card-header">
            <div>
                <div class="wp-card-title">Response Time Telemetry</div>
                <div class="wp-card-subtitle">Real-time round-trip latency in milliseconds (Last 24 Hours)</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    latency_df = AnalyticsService.get_latency_timeseries(hours=24)
    render_latency_trend_chart(latency_df, threshold_ms=config.SLOW_RESPONSE_THRESHOLD_MS)

with col_chart_right:
    st.markdown(
        """
        <div class="wp-card-header">
            <div>
                <div class="wp-card-title">Fleet Distribution</div>
                <div class="wp-card-subtitle">Current health breakdown</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_status_donut(kpis)

st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)

# ----------------------------------------------------
# 3. Live Monitored Fleet (Card-Row Style)
# ----------------------------------------------------
st.markdown(
    """
    <div class="wp-card-header" style="margin-top: 1rem;">
        <div>
            <div class="wp-card-title">Target Endpoints & Health</div>
            <div class="wp-card-subtitle">Continuous availability status, response codes, and manual check actions</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with get_db() as session:
    websites = WebsiteRepository.get_all(session, include_inactive=True)

if not websites:
    st.info("No targets registered yet. Add a website or API in the **1_Monitored_Websites** tab to begin monitoring.")
else:
    # Table Header Row
    th_col1, th_col2, th_col3, th_col4, th_col5, th_col6, th_col7 = st.columns([3.2, 1.8, 1.4, 1.4, 1.4, 2, 1.5])
    th_col1.markdown("<span style='font-size:0.75rem;font-weight:700;color:#64748b;text-transform:uppercase;'>ENDPOINT TARGET</span>", unsafe_allow_html=True)
    th_col2.markdown("<span style='font-size:0.75rem;font-weight:700;color:#64748b;text-transform:uppercase;'>STATUS</span>", unsafe_allow_html=True)
    th_col3.markdown("<span style='font-size:0.75rem;font-weight:700;color:#64748b;text-transform:uppercase;'>LATENCY</span>", unsafe_allow_html=True)
    th_col4.markdown("<span style='font-size:0.75rem;font-weight:700;color:#64748b;text-transform:uppercase;'>HTTP CODE</span>", unsafe_allow_html=True)
    th_col5.markdown("<span style='font-size:0.75rem;font-weight:700;color:#64748b;text-transform:uppercase;'>24H UPTIME</span>", unsafe_allow_html=True)
    th_col6.markdown("<span style='font-size:0.75rem;font-weight:700;color:#64748b;text-transform:uppercase;'>LAST CHECKED (UTC)</span>", unsafe_allow_html=True)
    th_col7.markdown("<span style='font-size:0.75rem;font-weight:700;color:#64748b;text-transform:uppercase;'>ACTION</span>", unsafe_allow_html=True)

    st.markdown("<div style='height: 1px; background: #e2e8f0; margin: 0.35rem 0 0.85rem 0;'></div>", unsafe_allow_html=True)

    yesterday = AnalyticsService.get_time_window("24h")

    for w in websites:
        with get_db() as session:
            latest = WebsiteRepository.get_latest_result(session, w.id)
            uptime_info = AnalyticsService.calculate_website_uptime(w.id, start_time=yesterday)

        # Status determination
        if not w.is_active:
            status_text = "Paused"
        elif not latest:
            status_text = "Pending"
        elif not latest.is_available:
            status_text = "Down"
        elif latest.response_time_ms and latest.response_time_ms >= config.SLOW_RESPONSE_THRESHOLD_MS:
            status_text = "Degraded"
        else:
            status_text = "Operational"

        c1, c2, c3, c4, c5, c6, c7 = st.columns([3.2, 1.8, 1.4, 1.4, 1.4, 2, 1.5])

        with c1:
            st.markdown(
                f"""
                <div style="line-height: 1.25;">
                    <span style="font-weight: 700; color: #0f172a; font-size: 0.92rem;">{w.name}</span><br>
                    <a href="{w.url}" target="_blank" style="font-size: 0.78rem; color: #64748b; text-decoration: none; font-family: monospace;">{w.url}</a>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(render_badge(status_text), unsafe_allow_html=True)
        with c3:
            if latest and latest.response_time_ms is not None:
                color = "#ef4444" if latest.response_time_ms >= config.SLOW_RESPONSE_THRESHOLD_MS else "#0f172a"
                st.markdown(f"<span class='wp-tag-latency' style='color:{color};'>{latest.response_time_ms} ms</span>", unsafe_allow_html=True)
            else:
                st.write("--")
        with c4:
            if latest and latest.http_status_code:
                st.markdown(f"<span class='wp-tag-code'>{latest.http_status_code}</span>", unsafe_allow_html=True)
            elif latest and latest.error_type:
                st.markdown(f"<span style='font-size:0.72rem;font-weight:600;color:#ef4444;'>{latest.error_type}</span>", unsafe_allow_html=True)
            else:
                st.write("--")
        with c5:
            if uptime_info["uptime_pct"] is not None:
                val = uptime_info["uptime_pct"]
                col = "#10b981" if val >= 99 else ("#f59e0b" if val >= 95 else "#ef4444")
                st.markdown(f"<span style='font-weight:700;color:{col};font-size:0.9rem;'>{val}%</span>", unsafe_allow_html=True)
            else:
                st.caption("No data")
        with c6:
            if latest and latest.checked_at:
                st.markdown(f"<span style='font-size:0.8rem;color:#475569;'>{latest.checked_at.strftime('%Y-%m-%d %H:%M:%S')}</span>", unsafe_allow_html=True)
            else:
                st.caption("Never checked")
        with c7:
            if st.button("⚡ Test", key=f"btn_check_{w.id}", use_container_width=True):
                with st.spinner(f"Pinging {w.name}..."):
                    res = MonitoringService.record_and_evaluate(w.id)
                    if res and res.is_available:
                        st.toast(f"✅ {w.name} is Operational ({res.response_time_ms}ms)", icon="⚡")
                    elif res:
                        st.toast(f"🚨 {w.name} Failed: {res.error_type}", icon="❌")
                st.rerun()

        st.markdown("<div style='height: 1px; background: #f1f5f9; margin: 0.5rem 0;'></div>", unsafe_allow_html=True)

# ----------------------------------------------------
# 4. Outage & Incident Log Preview
# ----------------------------------------------------
st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

with get_db() as session:
    recent_incidents = (
        session.query(Incident)
        .order_by(Incident.started_at.desc())
        .limit(5)
        .all()
    )

if recent_incidents:
    st.markdown(
        """
        <div class="wp-card-header">
            <div>
                <div class="wp-card-title">Recent Outages & Recovery Events</div>
                <div class="wp-card-subtitle">Automated incident tracking and downtime telemetry</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    inc_records = []
    for inc in recent_incidents:
        with get_db() as session:
            site = WebsiteRepository.get_by_id(session, inc.website_id)
            site_name = site.name if site else f"Site #{inc.website_id}"
        
        duration_display = f"{inc.duration_seconds}s" if inc.duration_seconds else ("Active Outage" if inc.status == "OPEN" else "--")
        inc_records.append({
            "Incident": f"#{inc.id}",
            "Website Target": site_name,
            "State": "🚨 OPEN" if inc.status == "OPEN" else "✅ RESOLVED",
            "Started At (UTC)": inc.started_at.strftime("%Y-%m-%d %H:%M:%S"),
            "Resolved At (UTC)": inc.resolved_at.strftime("%Y-%m-%d %H:%M:%S") if inc.resolved_at else "In Progress",
            "Total Outage Duration": duration_display,
            "Root Cause": inc.cause_summary or "HTTP check failure",
        })
    st.dataframe(pd.DataFrame(inc_records), use_container_width=True, hide_index=True)
