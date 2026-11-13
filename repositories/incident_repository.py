from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database.models import Incident, AlertHistory


class IncidentRepository:
    """Repository handling database operations for incidents and alert logs."""

    @staticmethod
    def get_open_incident(session: Session, website_id: int) -> Optional[Incident]:
        return (
            session.query(Incident)
            .filter(Incident.website_id == website_id, Incident.status == "OPEN")
            .order_by(desc(Incident.started_at))
            .first()
        )

    @staticmethod
    def create_incident(
        session: Session, website_id: int, started_at: datetime, cause_summary: str
    ) -> Incident:
        incident = Incident(
            website_id=website_id,
            started_at=started_at,
            status="OPEN",
            cause_summary=cause_summary,
        )
        session.add(incident)
        session.flush()
        return incident

    @staticmethod
    def resolve_incident(
        session: Session, incident_id: int, resolved_at: datetime
    ) -> Optional[Incident]:
        incident = session.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return None

        incident.status = "RESOLVED"
        incident.resolved_at = resolved_at
        if incident.started_at:
            delta = (resolved_at - incident.started_at).total_seconds()
            incident.duration_seconds = max(0, int(delta))

        session.flush()
        return incident

    @staticmethod
    def get_all(
        session: Session,
        website_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Incident]:
        query = session.query(Incident)
        if website_id is not None:
            query = query.filter(Incident.website_id == website_id)
        if status:
            query = query.filter(Incident.status == status)
        return query.order_by(desc(Incident.started_at)).limit(limit).all()

    @staticmethod
    def create_alert_log(
        session: Session,
        website_id: int,
        alert_type: str,
        delivery_status: str,
        incident_id: Optional[int] = None,
        recipient: Optional[str] = None,
        error_message: Optional[str] = None,
        sent_at: Optional[datetime] = None,
    ) -> AlertHistory:
        log = AlertHistory(
            website_id=website_id,
            incident_id=incident_id,
            alert_type=alert_type,
            delivery_status=delivery_status,
            recipient=recipient,
            error_message=error_message,
            sent_at=sent_at or datetime.now(timezone.utc).replace(tzinfo=None),
        )
        session.add(log)
        session.flush()
        return log

    @staticmethod
    def get_alert_logs(session: Session, limit: int = 50) -> List[AlertHistory]:
        return (
            session.query(AlertHistory)
            .order_by(desc(AlertHistory.sent_at))
            .limit(limit)
            .all()
        )
