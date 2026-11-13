import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from config import config
from database.models import Incident, Website, AlertHistory
from repositories.incident_repository import IncidentRepository

logger = logging.getLogger("webpulse.alert")


class AlertService:
    """Service managing email notifications for downtime incidents and operational recovery."""

    @classmethod
    def is_configured(cls) -> bool:
        """Check if SMTP notifications are enabled and required settings are filled."""
        return bool(
            config.SMTP_ENABLED
            and config.SMTP_HOST
            and config.SMTP_USER
            and config.ALERT_RECIPIENT
        )

    @classmethod
    def send_incident_alert(
        cls,
        session: Session,
        website: Website,
        incident: Incident,
        alert_type: str,  # 'DOWNTIME' or 'RECOVERY'
        detail_msg: Optional[str] = None,
    ) -> bool:
        """
        Send an email notification when downtime begins or recovers.
        Safely records delivery attempts in `alert_history`.
        Guarantees monitoring continues even if SMTP fails.
        """
        # Deduplication check: Do not re-send the same alert_type for the same incident
        existing_alert = (
            session.query(AlertHistory)
            .filter(
                AlertHistory.incident_id == incident.id,
                AlertHistory.alert_type == alert_type,
                AlertHistory.delivery_status == "SENT",
            )
            .first()
        )
        if existing_alert:
            logger.info(f"Skipping duplicate {alert_type} alert for incident #{incident.id} on {website.name}")
            return True

        recipient = config.ALERT_RECIPIENT

        if not cls.is_configured():
            logger.info(f"SMTP not configured/enabled. Logging SKIPPED alert for website '{website.name}'")
            IncidentRepository.create_alert_log(
                session=session,
                website_id=website.id,
                incident_id=incident.id,
                alert_type=alert_type,
                recipient=recipient or "Unconfigured",
                delivery_status="SKIPPED",
                error_message="SMTP alerts are disabled or not configured in environment.",
            )
            return False

        # Build Email Subject & Body
        if alert_type == "DOWNTIME":
            subject = f"[WebPulse ALERT] Outage Detected: {website.name}"
            body_text = (
                f"WebPulse Alert Notification\n\n"
                f"Website Outage Detected:\n"
                f"- Name: {website.name}\n"
                f"- URL: {website.url}\n"
                f"- Started At: {incident.started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                f"- Root Cause: {incident.cause_summary or 'Service unavailable'}\n"
                f"- Additional Info: {detail_msg or 'N/A'}\n\n"
                f"Please review the WebPulse dashboard for real-time status."
            )
        else:
            duration_str = f"{incident.duration_seconds}s" if incident.duration_seconds else "N/A"
            subject = f"[WebPulse RECOVERED] Operational: {website.name}"
            body_text = (
                f"WebPulse Recovery Notification\n\n"
                f"Website Has Recovered:\n"
                f"- Name: {website.name}\n"
                f"- URL: {website.url}\n"
                f"- Resolved At: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                f"- Total Downtime Duration: {duration_str}\n\n"
                f"The service is now responding normally."
            )

        try:
            msg = MIMEMultipart()
            msg["Subject"] = subject
            msg["From"] = config.SMTP_SENDER
            msg["To"] = recipient
            msg.attach(MIMEText(body_text, "plain"))

            # Connect and send via TLS
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10) as server:
                server.starttls()
                if config.SMTP_USER and config.SMTP_PASSWORD:
                    server.login(config.SMTP_USER, config.SMTP_PASSWORD)
                server.send_message(msg)

            logger.info(f"Successfully sent {alert_type} alert email to {recipient} for {website.name}")
            IncidentRepository.create_alert_log(
                session=session,
                website_id=website.id,
                incident_id=incident.id,
                alert_type=alert_type,
                recipient=recipient,
                delivery_status="SENT",
                error_message=None,
            )
            return True

        except Exception as err:
            err_msg = f"Failed to send email alert via {config.SMTP_HOST}:{config.SMTP_PORT} - {str(err)}"
            logger.error(err_msg)
            IncidentRepository.create_alert_log(
                session=session,
                website_id=website.id,
                incident_id=incident.id,
                alert_type=alert_type,
                recipient=recipient,
                delivery_status="FAILED",
                error_message=err_msg[:500],
            )
            return False
