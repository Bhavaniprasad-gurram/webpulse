from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database.models import Website, MonitoringResult, Incident


class WebsiteRepository:
    """Repository handling database operations for monitored website records."""

    @staticmethod
    def get_all(session: Session, include_inactive: bool = True) -> List[Website]:
        query = session.query(Website)
        if not include_inactive:
            query = query.filter(Website.is_active == True)
        return query.order_by(Website.name.asc()).all()

    @staticmethod
    def get_by_id(session: Session, website_id: int) -> Optional[Website]:
        return session.query(Website).filter(Website.id == website_id).first()

    @staticmethod
    def get_by_url(session: Session, url: str) -> Optional[Website]:
        return session.query(Website).filter(Website.url == url.strip()).first()

    @staticmethod
    def create(session: Session, data: Dict[str, Any]) -> Website:
        website = Website(
            name=data["name"].strip(),
            url=data["url"].strip(),
            monitoring_interval_seconds=int(data.get("monitoring_interval_seconds", 60)),
            timeout_seconds=int(data.get("timeout_seconds", 10)),
            is_active=bool(data.get("is_active", True)),
            description=data.get("description", "").strip() if data.get("description") else None,
            user_id=data.get("user_id"),
        )
        session.add(website)
        session.flush()
        return website

    @staticmethod
    def update(session: Session, website_id: int, updates: Dict[str, Any]) -> Optional[Website]:
        website = session.query(Website).filter(Website.id == website_id).first()
        if not website:
            return None

        if "name" in updates:
            website.name = updates["name"].strip()
        if "url" in updates:
            website.url = updates["url"].strip()
        if "monitoring_interval_seconds" in updates:
            website.monitoring_interval_seconds = int(updates["monitoring_interval_seconds"])
        if "timeout_seconds" in updates:
            website.timeout_seconds = int(updates["timeout_seconds"])
        if "is_active" in updates:
            website.is_active = bool(updates["is_active"])
        if "description" in updates:
            website.description = updates["description"].strip() if updates["description"] else None

        session.flush()
        return website

    @staticmethod
    def delete(session: Session, website_id: int) -> bool:
        website = session.query(Website).filter(Website.id == website_id).first()
        if not website:
            return False
        # Associated results and incidents cascade delete due to SQLAlchemy/DB foreign key constraints
        session.delete(website)
        session.flush()
        return True

    @staticmethod
    def toggle_active(session: Session, website_id: int) -> Optional[Website]:
        website = session.query(Website).filter(Website.id == website_id).first()
        if not website:
            return None
        website.is_active = not website.is_active
        session.flush()
        return website

    @staticmethod
    def get_latest_result(session: Session, website_id: int) -> Optional[MonitoringResult]:
        return (
            session.query(MonitoringResult)
            .filter(MonitoringResult.website_id == website_id)
            .order_by(desc(MonitoringResult.checked_at))
            .first()
        )

    @staticmethod
    def get_active_incident(session: Session, website_id: int) -> Optional[Incident]:
        return (
            session.query(Incident)
            .filter(Incident.website_id == website_id, Incident.status == "OPEN")
            .order_by(desc(Incident.started_at))
            .first()
        )
