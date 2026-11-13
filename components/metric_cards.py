import streamlit as st
from typing import Optional


def render_metric_card(
    label: str,
    value: str,
    subtext: Optional[str] = None,
    accent: str = "blue",
    icon: Optional[str] = None
):
    """
    Render a modern neo-SaaS KPI metric card with dynamic gradient accent top borders.
    Accents: 'blue', 'emerald', 'rose', 'indigo', 'amber'
    """
    icon_html = f"<span>{icon}</span> " if icon else ""
    subtext_html = f'<div class="wp-kpi-sub">{subtext}</div>' if subtext else ""
    
    html = f"""
    <div class="wp-kpi-card accent-{accent}">
        <div class="wp-kpi-label">{icon_html}{label}</div>
        <div class="wp-kpi-val">{value}</div>
        {subtext_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
