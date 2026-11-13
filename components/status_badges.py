import streamlit as st


def render_badge(status: str) -> str:
    """
    Return HTML markup for clean status pills.
    status options: 'Operational', 'Degraded', 'Down', 'Pending', 'Paused'
    """
    normalized = status.strip().lower()
    if normalized in ("operational", "up", "healthy"):
        css_class = "wp-badge-operational"
        label = "Operational"
    elif normalized in ("degraded", "slow", "warning"):
        css_class = "wp-badge-degraded"
        label = "Degraded"
    elif normalized in ("down", "outage", "failed"):
        css_class = "wp-badge-down"
        label = "Outage"
    elif normalized in ("paused", "inactive"):
        css_class = "wp-badge-paused"
        label = "Paused"
    else:
        css_class = "wp-badge-pending"
        label = "Pending Check"

    return f'<span class="wp-badge {css_class}">{label}</span>'


def display_badge(status: str):
    """Render status badge directly to Streamlit UI."""
    st.markdown(render_badge(status), unsafe_allow_html=True)
