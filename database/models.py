from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now():
    """Return timezone-aware or naive UTC datetime for standard SQLAlchemy storage."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    """User accounts model for website ownership and role management."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    websites = relationship("Website", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class Website(Base):
    """Registered targets monitored for availability and uptime."""
    __tablename__ = "websites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(150), nullable=False)
    url = Column(String(2048), nullable=False)
    monitoring_interval_seconds = Column(Integer, default=60, nullable=False)
    timeout_seconds = Column(Integer, default=10, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="websites")
    monitoring_results = relationship(
        "MonitoringResult", back_populates="website", cascade="all, delete-orphan", order_by="desc(MonitoringResult.checked_at)"
    )
    incidents = relationship(
        "Incident", back_populates="website", cascade="all, delete-orphan", order_by="desc(Incident.started_at)"
    )
    alerts = relationship(
        "AlertHistory", back_populates="website", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_website_active_interval", "is_active", "monitoring_interval_seconds"),
    )

    def __repr__(self):
        return f"<Website(id={self.id}, name='{self.name}', url='{self.url}', active={self.is_active})>"


class MonitoringResult(Base):
    """Historical records of individual HTTP availability checks."""
    __tablename__ = "monitoring_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    website_id = Column(Integer, ForeignKey("websites.id", ondelete="CASCADE"), nullable=False, index=True)
    checked_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    http_status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Float, nullable=True)
    is_available = Column(Boolean, nullable=False, index=True)
    error_type = Column(String(100), nullable=True)  # DNS_ERROR, TIMEOUT, SSL_ERROR, HTTP_4XX, HTTP_5XX, etc.
    error_message = Column(Text, nullable=True)

    # Relationships
    website = relationship("Website", back_populates="monitoring_results")

    __table_args__ = (
        Index("idx_results_website_checked", "website_id", "checked_at"),
        Index("idx_results_avail_checked", "is_available", "checked_at"),
    )

    def __repr__(self):
        return (
            f"<MonitoringResult(id={self.id}, website_id={self.website_id}, "
            f"code={self.http_status_code}, time_ms={self.response_time_ms}, avail={self.is_available})>"
        )


class Incident(Base):
    """Downtime incident tracking outages, root cause, and recovery duration."""
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    website_id = Column(Integer, ForeignKey("websites.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    status = Column(String(50), default="OPEN", nullable=False, index=True)  # 'OPEN' or 'RESOLVED'
    cause_summary = Column(String(255), nullable=True)

    # Relationships
    website = relationship("Website", back_populates="incidents")
    alerts = relationship("AlertHistory", back_populates="incident", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_incidents_website_status", "website_id", "status"),
    )

    def __repr__(self):
        return f"<Incident(id={self.id}, website_id={self.website_id}, status='{self.status}', started='{self.started_at}')>"


class AlertHistory(Base):
    """Audit log of alert notifications triggered and delivered."""
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=True, index=True)
    website_id = Column(Integer, ForeignKey("websites.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)  # 'DOWNTIME' or 'RECOVERY'
    recipient = Column(String(255), nullable=True)
    sent_at = Column(DateTime, default=utc_now, nullable=False)
    delivery_status = Column(String(50), nullable=False)  # 'SENT', 'FAILED', 'SKIPPED'
    error_message = Column(Text, nullable=True)

    # Relationships
    website = relationship("Website", back_populates="alerts")
    incident = relationship("Incident", back_populates="alerts")

    def __repr__(self):
        return f"<AlertHistory(id={self.id}, type='{self.alert_type}', status='{self.delivery_status}')>"
