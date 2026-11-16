import streamlit as st
from config import config
from database.connection import test_connection


def render_sidebar():
    """Left navigation: brand, system status, worker info."""
    with st.sidebar:
        # Brand
        st.markdown(
            """
            <div style="padding: 0.6rem 0 1.25rem 0; border-bottom: 1px solid #1e293b; margin-bottom: 1.25rem;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="background: #1e3a5f; width: 38px; height: 38px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 700; color: #ffffff; font-size: 1rem;">W</div>
                    <div>
                        <div style="font-size: 1.2rem; font-weight: 700; color: #ffffff; line-height: 1.1;">WebPulse</div>
                        <div style="font-size: 0.72rem; color: #94a3b8;">Website monitoring</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # System status
        st.markdown(
            "<div style='font-size: 0.7rem; text-transform: uppercase; color: #64748b; font-weight: 700; letter-spacing: 0.08em; margin-bottom: 0.6rem;'>System status</div>",
            unsafe_allow_html=True,
        )

        db_ok, db_msg = test_connection()
        if db_ok:
            st.markdown(
                """
                <div style="display: flex; align-items: center; gap: 8px; background: #0f172a; border: 1px solid #14532d; border-radius: 8px; padding: 0.5rem 0.75rem; margin-bottom: 0.75rem;">
                    <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #22c55e;"></span>
                    <span style="font-size: 0.8rem; font-weight: 600; color: #4ade80;">Database connected</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="display: flex; align-items: center; gap: 8px; background: #0f172a; border: 1px solid #7f1d1d; border-radius: 8px; padding: 0.5rem 0.75rem; margin-bottom: 0.75rem;">
                    <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #ef4444;"></span>
                    <span style="font-size: 0.8rem; font-weight: 600; color: #f87171;">Database offline</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.caption(f"Error: {db_msg[:60]}")

        # Background worker info
        st.markdown(
            f"""
            <div style="margin-top: 0.75rem; padding: 0.85rem; background: #0f172a; border-radius: 8px; font-size: 0.75rem; color: #94a3b8; border: 1px solid #1e293b;">
                <div style="font-weight: 700; color: #f8fafc; margin-bottom: 6px;">Background worker</div>
                <div style="line-height: 1.6;">
                    Check interval: <b style="color: #f1f5f9;">{config.DEFAULT_INTERVAL_SECONDS}s</b><br>
                    Failures before incident: <b style="color: #f1f5f9;">{config.FAILURE_THRESHOLD}</b><br>
                    Run it with:
                    <div style="background: #020617; padding: 4px 6px; border-radius: 4px; margin-top: 4px; font-family: monospace; color: #7dd3fc; overflow-x: auto;">python -m workers.monitor_worker</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
        st.caption("WebPulse")
