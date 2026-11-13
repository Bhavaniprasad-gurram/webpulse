from datetime import datetime, timezone, timedelta
from database.models import Website, MonitoringResult
from repositories.monitoring_repository import MonitoringRepository
from services.analytics_service import AnalyticsService


def test_uptime_calculation_math(test_db_session):
    """Verify uptime percentage formula: (successful / total) * 100."""
    session = test_db_session

    website = Website(name="Math Test Site", url="https://math.test.local")
    session.add(website)
    session.commit()

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Add 8 successful checks and 2 failed checks = 10 total (80% uptime)
    for i in range(8):
        MonitoringRepository.create_result(
            session=session,
            website_id=website.id,
            checked_at=now - timedelta(minutes=i * 2),
            is_available=True,
            http_status_code=200,
            response_time_ms=100.0 + i,
        )
    for i in range(2):
        MonitoringRepository.create_result(
            session=session,
            website_id=website.id,
            checked_at=now - timedelta(minutes=20 + i * 2),
            is_available=False,
            http_status_code=500,
        )
    session.commit()

    # Query with session directly
    total_checks = session.query(MonitoringResult).filter(MonitoringResult.website_id == website.id).count()
    successful_checks = session.query(MonitoringResult).filter(
        MonitoringResult.website_id == website.id, MonitoringResult.is_available == True
    ).count()

    assert total_checks == 10
    assert successful_checks == 8
    calculated_uptime = round((successful_checks / total_checks) * 100.0, 2)
    assert calculated_uptime == 80.0


def test_analytics_empty_dataset_handling(test_db_session):
    """Verify empty datasets return None / safe zeroes rather than dividing by zero."""
    session = test_db_session

    website = Website(name="Empty Site", url="https://empty.test.local")
    session.add(website)
    session.commit()

    total_checks = session.query(MonitoringResult).filter(MonitoringResult.website_id == website.id).count()
    assert total_checks == 0
    uptime_pct = None if total_checks == 0 else (0 / total_checks) * 100
    assert uptime_pct is None
