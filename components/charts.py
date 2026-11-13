import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from typing import Dict, Any


def render_latency_trend_chart(df: pd.DataFrame, threshold_ms: int = 1500):
    """Render interactive response time trend chart with polished gridlines, hover cards, and threshold line."""
    if df.empty or "checked_at" not in df.columns:
        st.info("No latency datapoints recorded yet for the selected period.")
        return

    # Palette for multiple sites: indigo, emerald, violet, sky, amber
    palette = ["#4f46e5", "#10b981", "#8b5cf6", "#0284c7", "#f59e0b", "#ec4899"]

    fig = px.line(
        df,
        x="checked_at",
        y="response_time_ms",
        color="website_name",
        markers=True,
        color_discrete_sequence=palette,
        labels={
            "checked_at": "Timestamp (UTC)",
            "response_time_ms": "Latency (ms)",
            "website_name": "Target",
        },
    )

    # Reference warning line for slow responses
    fig.add_hline(
        y=threshold_ms,
        line_dash="dash",
        line_color="#f59e0b",
        line_width=1.5,
        annotation_text=f"Degraded Threshold ({threshold_ms}ms)",
        annotation_position="top right",
        annotation_font=dict(size=10, color="#b45309", family="Plus Jakarta Sans"),
    )

    fig.update_traces(
        line=dict(width=2.5),
        marker=dict(size=6, line=dict(width=1, color="#ffffff")),
        hovertemplate="<b>%{fullData.name}</b><br>Time: %{x|%b %d, %H:%M:%S}<br>Latency: <b>%{y:.1f} ms</b><extra></extra>",
    )

    fig.update_layout(
        template="plotly_white",
        font=dict(family="Plus Jakarta Sans, sans-serif", color="#475569", size=11),
        hovermode="x unified",
        margin=dict(l=15, r=15, t=30, b=15),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            title="",
            font=dict(size=11),
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor="#f1f5f9",
            linecolor="#e2e8f0",
            tickfont=dict(size=10),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#f1f5f9",
            linecolor="#e2e8f0",
            ticksuffix=" ms",
            tickfont=dict(size=10),
        ),
        height=340,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_uptime_bar_chart(df: pd.DataFrame):
    """Render sleek modern uptime percentage comparison bar chart."""
    if df.empty or "uptime_pct" not in df.columns:
        st.info("No monitoring history available to compute uptime.")
        return

    valid_df = df[df["uptime_pct"].notna()].copy()
    if valid_df.empty:
        st.info("No valid checks recorded to calculate uptime comparison.")
        return

    colors = []
    for val in valid_df["uptime_pct"]:
        if val >= 99.0:
            colors.append("#10b981")  # Emerald
        elif val >= 95.0:
            colors.append("#f59e0b")  # Amber
        else:
            colors.append("#ef4444")  # Rose

    fig = go.Figure(
        data=[
            go.Bar(
                x=valid_df["name"],
                y=valid_df["uptime_pct"],
                marker=dict(
                    color=colors,
                    line=dict(width=0),
                    cornerradius=6,
                ),
                text=[f"<b>{v:.1f}%</b>" for v in valid_df["uptime_pct"]],
                textposition="auto",
                textfont=dict(size=11, family="Plus Jakarta Sans"),
                hovertemplate="<b>%{x}</b><br>Uptime: <b>%{y:.2f}%</b><extra></extra>",
            )
        ]
    )

    fig.update_layout(
        template="plotly_white",
        font=dict(family="Plus Jakarta Sans, sans-serif", color="#475569", size=11),
        yaxis=dict(
            range=[0, 108],
            title="",
            ticksuffix="%",
            gridcolor="#f1f5f9",
            linecolor="#e2e8f0",
        ),
        xaxis=dict(title="", linecolor="#e2e8f0"),
        margin=dict(l=15, r=15, t=25, b=15),
        height=300,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_status_donut(summary: Dict[str, Any]):
    """Render modern fleet health distribution donut chart with clean legend."""
    labels = ["Operational", "Degraded (Slow)", "Outage", "Pending"]
    values = [
        summary.get("operational_count", 0),
        summary.get("degraded_count", 0),
        summary.get("down_count", 0),
        summary.get("pending_count", 0),
    ]
    colors = ["#10b981", "#f59e0b", "#ef4444", "#94a3b8"]

    if sum(values) == 0:
        st.info("No targets registered yet.")
        return

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.68,
                marker=dict(colors=colors, line=dict(color="#ffffff", width=2)),
                textinfo="value",
                textfont=dict(family="Plus Jakarta Sans", size=12, color="#ffffff"),
                hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>",
            )
        ]
    )

    # Center total count text annotation
    total = sum(values)
    fig.add_annotation(
        text=f"<b style='font-size:22px;color:#0f172a;'>{total}</b><br><span style='font-size:11px;color:#64748b;'>TOTAL</span>",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(family="Plus Jakarta Sans"),
    )

    fig.update_layout(
        template="plotly_white",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(family="Plus Jakarta Sans", size=10),
        ),
        margin=dict(l=10, r=10, t=10, b=30),
        height=290,
    )
    st.plotly_chart(fig, use_container_width=True)
