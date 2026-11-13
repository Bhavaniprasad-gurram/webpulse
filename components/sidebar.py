import streamlit as st
from config import config
from database.connection import test_connection


def render_sidebar():
    """Render sleek modern dark navigation sidebar with real-time indicators."""
    with st.sidebar:
        # Brand Header with sleek gradient badge
        st.markdown(
            """
            <div style="padding: 0.6rem 0 1.25rem 0; border-bottom: 1px solid #1e293b; margin-bottom: 1.25rem;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="background: linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%); width: 38px; height: 38px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-weight: 800; color: #ffffff; font-size: 1.15rem; box-shadow: 0 4px 12px rgba(79, 70, 229, 0.35);">WP</div>
                    <div>
                        <div style="font-size: 1.2rem; font-weight: 800; color: #ffffff; letter-spacing: -0.02em; line-height: 1.1;">WebPulse</div>
                        <div style="font-size: 0.72rem; color: #94a3b8; font-weight: 500; letter-spacing: 0.02em;">Uptime & Observability</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Telemetry Status Section
        st.markdown(
            """
            <div style="margin-bottom: 0.85rem;">
                <div style="font-size: 0.7rem; text-transform: uppercase; color: #64748b; font-weight: 700; letter-spacing: 0.08em;">SYSTEM HEALTH</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        db_ok, db_msg = test_connection()
        if db_ok:
            st.markdown(
                """
                <div style="display: flex; align-items: center; gap: 8px; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 8px; padding: 0.5rem 0.75rem; margin-bottom: 0.75rem;">
                    <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #10b981; box-shadow: 0 0 8px #10b981;"></span>
                    <span style="font-size: 0.8rem; font-weight: 600; color: #34d399;">Database Connected</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="display: flex; align-items: center; gap: 8px; background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.25); border-radius: 8px; padding: 0.5rem 0.75rem; margin-bottom: 0.75rem;">
                    <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #ef4444; box-shadow: 0 0 8px #ef4444;"></span>
                    <span style="font-size: 0.8rem; font-weight: 600; color: #f87171;">DB Offline</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.caption(f"Error: {db_msg[:45]}...")

        # Background Worker Status Info Box
        st.markdown(
            f"""
            <div style="margin-top: 0.75rem; padding: 0.85rem; background: #0f172a; border-radius: 10px; font-size: 0.75rem; color: #94a3b8; border: 1px solid #1e293b;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="font-weight: 700; color: #f8fafc;">Worker Polling</span>
                    <span style="background: rgba(99, 102, 241, 0.2); color: #818cf8; font-size: 0.68rem; padding: 2px 6px; border-radius: 4px; font-weight: 600;">ACTIVE</span>
                </div>
                <div style="line-height: 1.5;">
                    • Interval: <b style="color: #f1f5f9;">{config.DEFAULT_INTERVAL_SECONDS}s</b><br>
                    • Threshold: <b style="color: #f1f5f9;">{config.FAILURE_THRESHOLD} fails</b><br>
                    • Worker cmd:
                    <div style="background: #020617; padding: 4px 6px; border-radius: 4px; margin-top: 4px; font-family: monospace; color: #38bdf8; overflow-x: auto;">
                        python -m workers.monitor_worker
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
        st.caption("WebPulse v2.0 • Production Portfolio Edition")
