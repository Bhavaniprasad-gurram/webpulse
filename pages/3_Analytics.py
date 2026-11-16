from pathlib import Path
from datetime import datetime, timezone
import streamlit as st
import pandas as pd

# Page Configuration
st.set_page_config(page_title="Analytics — WebPulse", layout="wide")

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
from services.analytics_service import AnalyticsService
from components.sidebar import render_sidebar
from components.metric_cards import render_metric_card
from components.charts import render_latency_trend_chart, render_uptime_bar_chart

render_sidebar()

st.title("Analytics")
st.caption("Response times, uptime and past checks for the selected period.")

# ----------------------------------------------------
# Filter Controls
# ----------------------------------------------------
col_f1, col_f2, col_f3 = st.columns([2, 3, 1])

with col_f1:
    period_label = st.selectbox("Time period", options=["Last 24 Hours", "Last 7 Days", "Last 30 Days"], index=0)
    period_code = "24h" if "24" in period_label else ("7d" if "7" in period_label else "30d")
    start_dt = AnalyticsService.get_time_window(period_code)

with col_f2:
    with get_db() as session:
        all_sites = WebsiteRepository.get_all(session, include_inactive=True)
    site_dict = {"All websites": None}
    for s in all_sites:
        site_dict[s.name] = s.id
    selected_site_name = st.selectbox("Website", options=list(site_dict.keys()))
    selected_site_id = site_dict[selected_site_name]

with col_f3:
    st.write("")
    if st.button("Refresh", use_container_width=True):
        st.rerun()

st.markdown("<div class='wp-section-header'></div>", unsafe_allow_html=True)

# ----------------------------------------------------
# 1. Summary Statistics for Window
# ----------------------------------------------------
resp_stats = AnalyticsService.calculate_response_time_stats(website_id=selected_site_id, start_time=start_dt)

c1, c2, c3, c4 = st.columns(4)
with c1:
    avg_s = f"{resp_stats['avg_ms']} ms" if resp_stats['avg_ms'] is not None else "--"
    render_metric_card("Average response time", avg_s, f"Selected period ({period_label})")
with c2:
    min_s = f"{resp_stats['min_ms']} ms" if resp_stats['min_ms'] is not None else "--"
    render_metric_card("Fastest response", min_s, "Fastest check in this period")
with c3:
    max_s = f"{resp_stats['max_ms']} ms" if resp_stats['max_ms'] is not None else "--"
    render_metric_card("Slowest response", max_s, "Slowest check in this period")
with c4:
    render_metric_card("Total checks", str(resp_stats["sample_count"]), "Checks recorded in this period")

st.markdown("<div class='wp-section-header'></div>", unsafe_allow_html=True)

# ----------------------------------------------------
# 2. Charts
# ----------------------------------------------------
col_c1, col_c2 = st.columns([6, 4])

with col_c1:
    st.subheader(f"Response time ({period_label})")
    hours_map = {"24h": 24, "7d": 168, "30d": 720}
    hours_to_fetch = hours_map.get(period_code, 24)
    trend_df = AnalyticsService.get_latency_timeseries(website_id=selected_site_id, hours=hours_to_fetch)
    render_latency_trend_chart(trend_df, threshold_ms=config.SLOW_RESPONSE_THRESHOLD_MS)

with col_c2:
    st.subheader(f"Uptime by website ({period_label})")
    comp_df = AnalyticsService.get_website_comparison(period=period_code)
    if selected_site_id:
        comp_df = comp_df[comp_df["id"] == selected_site_id]
    render_uptime_bar_chart(comp_df)

st.markdown("<div class='wp-section-header'></div>", unsafe_allow_html=True)

# ----------------------------------------------------
# 3. Check history
# ----------------------------------------------------
st.subheader("Check history")

col_log1, col_log2 = st.columns([2, 2])
with col_log1:
    avail_filter = st.selectbox("Status", options=["All Results", "Up Only", "Down Only"])
with col_log2:
    limit_select = st.selectbox("Rows per page", options=[25, 50, 100], index=1)

is_avail_param = None
if avail_filter == "Up Only":
    is_avail_param = True
elif avail_filter == "Down Only":
    is_avail_param = False

with get_db() as session:
    results, total_count = MonitoringRepository.query_history(
        session=session,
        website_id=selected_site_id,
        is_available=is_avail_param,
        start_date=start_dt,
        limit=limit_select,
        offset=0,
    )

st.caption(f"Showing up to {limit_select} of {total_count} matching checks.")

if not results:
    st.info("No checks found for this filter.")
else:
    table_rows = []
    for r in results:
        with get_db() as session:
            s_obj = WebsiteRepository.get_by_id(session, r.website_id)
            s_name = s_obj.name if s_obj else f"Site #{r.website_id}"

        table_rows.append({
            "Checked at": r.checked_at.strftime("%Y-%m-%d %H:%M:%S"),
            "Website": s_name,
            "Status": "Up" if r.is_available else "Down",
            "HTTP code": r.http_status_code or "--",
            "Response time (ms)": r.response_time_ms if r.response_time_ms is not None else "--",
            "Error type": r.error_type or "None",
            "Error": r.error_message or "--",
        })
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
