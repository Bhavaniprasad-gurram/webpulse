from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from database.models import Website, MonitoringResult, Incident
from repositories.monitoring_repository import MonitoringRepository
from repositories.incident_repository import IncidentRepository
from services.incident_service import IncidentService
from services.monitoring_service import CheckResult


def test_incident_lifecycle_and_threshold(test_db_session):
    """
    Test that an incident is only opened when consecutive failures meet the threshold,
    remains open without duplicate incidents, and resolves properly upon recovery.
    """
    session = test_db_session

    # 1. Create a monitored website
    website = Website(
        name="Test API",
        url="https://api.test.local",
        monitoring_interval_seconds=60,
        timeout_seconds=10,
        is_active=True,
    )
    session.add(website)
    session.commit()

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # 2. Check 1 (Failure) - Should NOT trigger incident (threshold is 2)
    chk1 = MonitoringRepository.create_result(
        session=session,
        website_id=website.id,
        checked_at=now - timedelta(minutes=2),
        is_available=False,
        error_type="CONNECTION_TIMEOUT",
        error_message="Timed out",
    )
    session.commit()

    inc1 = IncidentService.process_result(session, website.id, chk1)
    session.commit()
    assert inc1 is None
    assert session.query(Incident).count() == 0

    # 3. Check 2 (Second Consecutive Failure) - Meets threshold (2), opens incident
    chk2 = MonitoringRepository.create_result(
        session=session,
        website_id=website.id,
        checked_at=now - timedelta(minutes=1),
        is_available=False,
        error_type="CONNECTION_TIMEOUT",
        error_message="Timed out",
    )
    session.commit()

    inc2 = IncidentService.process_result(session, website.id, chk2)
    session.commit()
    assert inc2 is not None
    assert inc2.status == "OPEN"
    assert session.query(Incident).count() == 1

    # 4. Check 3 (Third Consecutive Failure) - Must NOT create duplicate incident
    chk3 = MonitoringRepository.create_result(
        session=session,
        website_id=website.id,
        checked_at=now,
        is_available=False,
        error_type="CONNECTION_TIMEOUT",
        error_message="Timed out",
    )
    session.commit()

    inc3 = IncidentService.process_result(session, website.id, chk3)
    session.commit()
    assert inc3.id == inc2.id
    assert session.query(Incident).count() == 1

    # 5. Check 4 (Recovery / Success) - Resolves the incident
    chk4 = MonitoringRepository.create_result(
        session=session,
        website_id=website.id,
        checked_at=now + timedelta(minutes=1),
        is_available=True,
        http_status_code=200,
        response_time_ms=120.5,
    )
    session.commit()

    inc4 = IncidentService.process_result(session, website.id, chk4)
    session.commit()
    assert inc4 is not None
    assert inc4.status == "RESOLVED"
    assert inc4.resolved_at is not None
    assert inc4.duration_seconds is not None
    assert inc4.duration_seconds >= 0

    # Verify no open incidents remain
    open_inc = IncidentRepository.get_open_incident(session, website.id)
    assert open_inc is None
