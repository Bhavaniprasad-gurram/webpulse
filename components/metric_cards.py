import streamlit as st
from typing import Optional


def render_metric_card(
    label: str,
    value: str,
    subtext: Optional[str] = None,
    accent: str = "blue",
):
    """One KPI card: label on top, big value, small subtext below."""
    subtext_html = f'<div class="wp-kpi-sub">{subtext}</div>' if subtext else ""
    html = f"""
    <div class="wp-kpi-card accent-{accent}">
        <div class="wp-kpi-label">{label}</div>
        <div class="wp-kpi-val">{value}</div>
        {subtext_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
