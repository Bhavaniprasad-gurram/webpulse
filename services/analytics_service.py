from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
import pandas as pd
from sqlalchemy import func
from config import config
from database.connection import get_db
from database.models import Website, MonitoringResult, Incident
from repositories.website_repository import WebsiteRepository


class AnalyticsService:
    """Service providing uptime calculations, latency metrics, and time-series aggregations."""

    @classmethod
    def get_time_window(cls, period: str) -> Optional[datetime]:
        """Convert period string ('24h', '7d', '30d') to UTC start datetime."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if period == "24h":
            return now - timedelta(hours=24)
        elif period == "7d":
            return now - timedelta(days=7)
        elif period == "30d":
            return now - timedelta(days=30)
        return None

    @classmethod
    def calculate_website_uptime(
        cls, website_id: int, start_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calculate uptime percentage and check counts for a given website.
        Formula: (Successful checks / Total valid checks) * 100
        Returns None for uptime_pct if no checks exist.
        """
        with get_db() as session:
            query = session.query(MonitoringResult).filter(MonitoringResult.website_id == website_id)
            if start_time:
                query = query.filter(MonitoringResult.checked_at >= start_time)

            total_checks = query.count()
            if total_checks == 0:
                return {
                    "total_checks": 0,
                    "successful_checks": 0,
                    "failed_checks": 0,
                    "uptime_pct": None,
                }

            successful_checks = query.filter(MonitoringResult.is_available == True).count()
            failed_checks = total_checks - successful_checks
            uptime_pct = round((successful_checks / total_checks) * 100.0, 2)

            return {
                "total_checks": total_checks,
                "successful_checks": successful_checks,
                "failed_checks": failed_checks,
                "uptime_pct": uptime_pct,
            }

    @classmethod
    def calculate_response_time_stats(
        cls, website_id: Optional[int] = None, start_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Calculate avg, min, max response times in milliseconds."""
        with get_db() as session:
            query = session.query(
                func.avg(MonitoringResult.response_time_ms).label("avg_time"),
                func.min(MonitoringResult.response_time_ms).label("min_time"),
                func.max(MonitoringResult.response_time_ms).label("max_time"),
                func.count(MonitoringResult.id).label("total"),
            ).filter(MonitoringResult.response_time_ms.isnot(None))

            if website_id is not None:
                query = query.filter(MonitoringResult.website_id == website_id)
            if start_time is not None:
                query = query.filter(MonitoringResult.checked_at >= start_time)

            result = query.one()
            avg_val = round(float(result.avg_time), 1) if result.avg_time is not None else None
            min_val = round(float(result.min_time), 1) if result.min_time is not None else None
            max_val = round(float(result.max_time), 1) if result.max_time is not None else None

            return {
                "avg_ms": avg_val,
                "min_ms": min_val,
                "max_ms": max_val,
                "sample_count": result.total or 0,
            }

    @classmethod
    def get_overall_system_kpis(cls) -> Dict[str, Any]:
        """Summary metrics across all monitored websites for dashboard header cards."""
        with get_db() as session:
            websites = WebsiteRepository.get_all(session, include_inactive=True)
            total_count = len(websites)
            operational_count = 0
            down_count = 0
            degraded_count = 0
            pending_count = 0

            slow_threshold = config.SLOW_RESPONSE_THRESHOLD_MS

            for w in websites:
                latest = WebsiteRepository.get_latest_result(session, w.id)
                if not latest:
                    pending_count += 1
                elif not latest.is_available:
                    down_count += 1
                elif latest.response_time_ms and latest.response_time_ms >= slow_threshold:
                    degraded_count += 1
                else:
                    operational_count += 1

            # System-wide 24h uptime
            yesterday = cls.get_time_window("24h")
            q_24h = session.query(MonitoringResult).filter(MonitoringResult.checked_at >= yesterday)
            total_24h = q_24h.count()
            if total_24h > 0:
                success_24h = q_24h.filter(MonitoringResult.is_available == True).count()
                system_uptime_24h = round((success_24h / total_24h) * 100.0, 2)
            else:
                system_uptime_24h = None

            # Average response time across system in last 24h
            stats_24h = cls.calculate_response_time_stats(start_time=yesterday)

            # Active incidents count
            active_incidents = (
                session.query(Incident).filter(Incident.status == "OPEN").count()
            )

            return {
                "total_websites": total_count,
                "operational_count": operational_count,
                "down_count": down_count,
                "degraded_count": degraded_count,
                "pending_count": pending_count,
                "overall_uptime_24h": system_uptime_24h,
                "avg_response_time_ms": stats_24h["avg_ms"],
                "active_incidents": active_incidents,
            }

    @classmethod
    def get_latency_timeseries(
        cls, website_id: Optional[int] = None, hours: int = 24
    ) -> pd.DataFrame:
        """Fetch chronological latency datapoints for Plotly line charts."""
        start_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)
        with get_db() as session:
            query = (
                session.query(
                    MonitoringResult.checked_at,
                    MonitoringResult.response_time_ms,
                    MonitoringResult.is_available,
                    Website.name.label("website_name"),
                )
                .join(Website, Website.id == MonitoringResult.website_id)
                .filter(MonitoringResult.checked_at >= start_time)
            )

            if website_id:
                query = query.filter(MonitoringResult.website_id == website_id)

            query = query.order_by(MonitoringResult.checked_at.asc())
            rows = query.all()

            if not rows:
                return pd.DataFrame(columns=["checked_at", "response_time_ms", "is_available", "website_name"])

            data = [
                {
                    "checked_at": r.checked_at,
                    "response_time_ms": r.response_time_ms,
                    "is_available": r.is_available,
                    "website_name": r.website_name,
                }
                for r in rows
            ]
            return pd.DataFrame(data)

    @classmethod
    def get_website_comparison(cls, period: str = "7d") -> pd.DataFrame:
        """Comparison table and bar chart data for all websites."""
        start_time = cls.get_time_window(period)
        with get_db() as session:
            websites = WebsiteRepository.get_all(session, include_inactive=True)
            records = []
            for w in websites:
                uptime_data = cls.calculate_website_uptime(w.id, start_time)
                resp_data = cls.calculate_response_time_stats(w.id, start_time)
                latest = WebsiteRepository.get_latest_result(session, w.id)

                status_label = "Pending"
                if latest:
                    if not latest.is_available:
                        status_label = "Down"
                    elif latest.response_time_ms and latest.response_time_ms >= config.SLOW_RESPONSE_THRESHOLD_MS:
                        status_label = "Degraded"
                    else:
                        status_label = "Operational"

                records.append({
                    "id": w.id,
                    "name": w.name,
                    "url": w.url,
                    "status": status_label,
                    "is_active": w.is_active,
                    "uptime_pct": uptime_data["uptime_pct"],
                    "total_checks": uptime_data["total_checks"],
                    "avg_latency_ms": resp_data["avg_ms"],
                    "latest_code": latest.http_status_code if latest else None,
                    "last_checked": latest.checked_at if latest else None,
                })

            return pd.DataFrame(records)
