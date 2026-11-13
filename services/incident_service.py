import logging
from datetime import datetime, timezone
from typing import Optional, List, Any
from sqlalchemy.orm import Session
from config import config
from database.models import Website, Incident, MonitoringResult
from repositories.incident_repository import IncidentRepository
from repositories.monitoring_repository import MonitoringRepository
from repositories.website_repository import WebsiteRepository
from services.alert_service import AlertService

logger = logging.getLogger("webpulse.incident")


class IncidentService:
    """Service managing downtime incident lifecycle, failure thresholds, and state transitions."""

    @classmethod
    def process_result(cls, session: Session, website_id: int, latest_result: Any) -> Optional[Incident]:
        """
        Evaluate recent check results against the consecutive failure threshold
        and transition incident state between OPEN and RESOLVED.
        """
        website = WebsiteRepository.get_by_id(session, website_id)
        if not website:
            return None

        open_incident = IncidentRepository.get_open_incident(session, website_id)
        threshold = config.FAILURE_THRESHOLD

        if latest_result.is_available:
            # Service is operational
            if open_incident:
                # Resolve active downtime incident
                resolved_time = datetime.now(timezone.utc).replace(tzinfo=None)
                IncidentRepository.resolve_incident(
                    session=session,
                    incident_id=open_incident.id,
                    resolved_at=resolved_time,
                )
                session.flush()
                logger.info(
                    f"Resolved incident #{open_incident.id} for website '{website.name}'. "
                    f"Duration: {open_incident.duration_seconds}s"
                )
                # Dispatch recovery alert
                AlertService.send_incident_alert(
                    session=session,
                    website=website,
                    incident=open_incident,
                    alert_type="RECOVERY",
                )
                return open_incident
            return None

        # Service check failed (is_available == False)
        if open_incident:
            # Outage is already tracked; do not open duplicate incident
            logger.debug(f"Website '{website.name}' remains down. Incident #{open_incident.id} remains OPEN.")
            return open_incident

        # No active incident: check if consecutive failure threshold is satisfied
        recent_checks = MonitoringRepository.get_latest_consecutive(session, website_id, limit=threshold)
        
        # If we have fewer checks than the failure threshold, do not prematurely open an outage
        if len(recent_checks) < threshold:
            logger.info(
                f"Check failed for '{website.name}', but streak ({len(recent_checks)}) is below "
                f"threshold ({threshold}). Incident not opened yet."
            )
            return None

        # Verify all checks in the recent streak are failures
        all_failed = all(not r.is_available for r in recent_checks)
        if all_failed:
            # Started at earliest failed check in the streak
            earliest_in_streak = recent_checks[-1].checked_at if recent_checks else latest_result.checked_at
            cause = latest_result.error_type or "HTTP check failed"
            
            new_incident = IncidentRepository.create_incident(
                session=session,
                website_id=website_id,
                started_at=earliest_in_streak,
                cause_summary=cause,
            )
            session.flush()
            logger.warning(
                f"Consecutive failure threshold reached ({threshold}). Opened incident #{new_incident.id} "
                f"for website '{website.name}' due to {cause}."
            )
            # Dispatch downtime alert
            AlertService.send_incident_alert(
                session=session,
                website=website,
                incident=new_incident,
                alert_type="DOWNTIME",
                detail_msg=latest_result.error_message,
            )
            return new_incident

        return None
