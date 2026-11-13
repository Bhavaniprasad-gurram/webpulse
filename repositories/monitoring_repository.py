from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database.models import MonitoringResult


class MonitoringRepository:
    """Repository handling database operations for individual check results."""

    @staticmethod
    def create_result(session: Session, website_id: int, checked_at: datetime,
                      is_available: bool, http_status_code: Optional[int] = None,
                      response_time_ms: Optional[float] = None,
                      error_type: Optional[str] = None,
                      error_message: Optional[str] = None) -> MonitoringResult:
        result = MonitoringResult(
            website_id=website_id,
            checked_at=checked_at,
            http_status_code=http_status_code,
            response_time_ms=response_time_ms,
            is_available=is_available,
            error_type=error_type,
            error_message=error_message,
        )
        session.add(result)
        session.flush()
        return result

    @staticmethod
    def get_recent_by_website(session: Session, website_id: int, limit: int = 50) -> List[MonitoringResult]:
        return (
            session.query(MonitoringResult)
            .filter(MonitoringResult.website_id == website_id)
            .order_by(desc(MonitoringResult.checked_at))
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_latest_consecutive(session: Session, website_id: int, limit: int = 5) -> List[MonitoringResult]:
        """Fetch the most recent N checks in reverse chronological order."""
        return (
            session.query(MonitoringResult)
            .filter(MonitoringResult.website_id == website_id)
            .order_by(desc(MonitoringResult.checked_at))
            .limit(limit)
            .all()
        )

    @staticmethod
    def query_history(
        session: Session,
        website_id: Optional[int] = None,
        is_available: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[MonitoringResult], int]:
        """Paginated history query with filtering."""
        query = session.query(MonitoringResult)

        if website_id is not None:
            query = query.filter(MonitoringResult.website_id == website_id)
        if is_available is not None:
            query = query.filter(MonitoringResult.is_available == is_available)
        if start_date is not None:
            query = query.filter(MonitoringResult.checked_at >= start_date)
        if end_date is not None:
            query = query.filter(MonitoringResult.checked_at <= end_date)

        total_count = query.count()
        results = query.order_by(desc(MonitoringResult.checked_at)).offset(offset).limit(limit).all()
        return results, total_count
