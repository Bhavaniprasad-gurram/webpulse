import time
import logging
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional, Dict, Any
import requests
from database.connection import get_db
from database.models import Website, MonitoringResult
from repositories.monitoring_repository import MonitoringRepository
from repositories.website_repository import WebsiteRepository

logger = logging.getLogger("webpulse.monitoring")


@dataclass
class CheckResult:
    website_id: int
    url: str
    is_available: bool
    http_status_code: Optional[int]
    response_time_ms: Optional[float]
    error_type: Optional[str]
    error_message: Optional[str]
    checked_at: datetime


class MonitoringService:
    """Service performing real HTTP availability checks, error taxonomy, and persisting results."""

    USER_AGENT = "WebPulse/1.0 (+https://webpulse.local; website availability monitor)"

    @classmethod
    def check_website(cls, website: Website) -> CheckResult:
        """
        Execute an actual HTTP request against the website target.
        Measures latency, evaluates status codes, catches network/SSL exceptions,
        and classifies error categories.
        """
        checked_at = datetime.now(timezone.utc).replace(tzinfo=None)
        timeout = website.timeout_seconds or 10
        url = website.url

        headers = {
            "User-Agent": cls.USER_AGENT,
            "Accept": "*/*",
        }

        start_time = time.perf_counter()
        is_available = False
        status_code = None
        error_type = None
        error_message = None
        response_time_ms = None

        try:
            # Enforce SSL certificate verification; follow standard redirects
            response = requests.get(
                url,
                headers=headers,
                timeout=timeout,
                allow_redirects=True,
                verify=True,
            )
            elapsed = time.perf_counter() - start_time
            response_time_ms = round(elapsed * 1000, 2)
            status_code = response.status_code

            # Availability rules:
            # 2xx (Success) and 3xx (Redirect successfully completed) are operational.
            # 4xx (Client errors) and 5xx (Server outages) are downtime.
            if 200 <= status_code < 400:
                is_available = True
            elif 400 <= status_code < 500:
                is_available = False
                error_type = f"HTTP_{status_code}_CLIENT_ERROR"
                error_message = f"Client HTTP Error {status_code}: {response.reason}"
            else:
                is_available = False
                error_type = f"HTTP_{status_code}_SERVER_ERROR"
                error_message = f"Server Error {status_code}: {response.reason}"

        except requests.exceptions.SSLError as ssl_err:
            elapsed = time.perf_counter() - start_time
            response_time_ms = round(elapsed * 1000, 2)
            is_available = False
            error_type = "SSL_ERROR"
            error_message = f"SSL Certificate Verification Failed: {str(ssl_err)[:200]}"
            logger.warning(f"SSL error for {url}: {error_message}")

        except requests.exceptions.ConnectTimeout:
            elapsed = time.perf_counter() - start_time
            response_time_ms = round(elapsed * 1000, 2)
            is_available = False
            error_type = "CONNECTION_TIMEOUT"
            error_message = f"Connection timed out after {timeout} seconds."
            logger.warning(f"Timeout for {url}: {error_message}")

        except requests.exceptions.ReadTimeout:
            elapsed = time.perf_counter() - start_time
            response_time_ms = round(elapsed * 1000, 2)
            is_available = False
            error_type = "READ_TIMEOUT"
            error_message = f"Server accepted connection but failed to reply within {timeout}s read timeout."
            logger.warning(f"Read timeout for {url}: {error_message}")

        except requests.exceptions.ConnectionError as conn_err:
            elapsed = time.perf_counter() - start_time
            response_time_ms = round(elapsed * 1000, 2)
            is_available = False
            err_str = str(conn_err).lower()
            if "name or service not known" in err_str or "getaddrinfo failed" in err_str or "nodename nor servname" in err_str:
                error_type = "DNS_ERROR"
                error_message = "DNS Resolution Failed: domain could not be resolved."
            else:
                error_type = "CONNECTION_REFUSED"
                error_message = "Failed to establish TCP connection (Host unreachable or port refused)."
            logger.warning(f"Connection error for {url}: {error_message}")

        except requests.exceptions.RequestException as req_err:
            elapsed = time.perf_counter() - start_time
            response_time_ms = round(elapsed * 1000, 2)
            is_available = False
            error_type = "NETWORK_ERROR"
            error_message = f"Network Exception: {str(req_err)[:200]}"
            logger.warning(f"Request exception for {url}: {error_message}")

        except Exception as unexpected_err:
            elapsed = time.perf_counter() - start_time
            response_time_ms = round(elapsed * 1000, 2)
            is_available = False
            error_type = "UNKNOWN_ERROR"
            error_message = f"Unexpected failure: {str(unexpected_err)[:200]}"
            logger.error(f"Unexpected monitoring check failure for {url}: {unexpected_err}", exc_info=True)

        return CheckResult(
            website_id=website.id,
            url=url,
            is_available=is_available,
            http_status_code=status_code,
            response_time_ms=response_time_ms,
            error_type=error_type,
            error_message=error_message,
            checked_at=checked_at,
        )

    @classmethod
    def record_and_evaluate(cls, website_id: int) -> Optional[MonitoringResult]:
        """
        Perform a check for a website, persist the result, and trigger incident state analysis.
        Safe against individual website errors.
        """
        # Import IncidentService lazily to avoid circular imports
        from services.incident_service import IncidentService

        try:
            with get_db() as session:
                website = WebsiteRepository.get_by_id(session, website_id)
                if not website:
                    logger.error(f"Website ID {website_id} not found for monitoring check.")
                    return None
                
                # Clone lightweight info for execution
                w_id = website.id
                w_name = website.name
                w_url = website.url
                w_timeout = website.timeout_seconds

            # Execute HTTP check outside DB transaction to avoid holding open connection
            temp_obj = Website(id=w_id, name=w_name, url=w_url, timeout_seconds=w_timeout)
            check_result = cls.check_website(temp_obj)

            # Persist result and evaluate incidents
            with get_db() as session:
                result = MonitoringRepository.create_result(
                    session=session,
                    website_id=check_result.website_id,
                    checked_at=check_result.checked_at,
                    is_available=check_result.is_available,
                    http_status_code=check_result.http_status_code,
                    response_time_ms=check_result.response_time_ms,
                    error_type=check_result.error_type,
                    error_message=check_result.error_message,
                )
                session.commit()
                # Run incident detection logic
                IncidentService.process_result(session, w_id, check_result)
                return result

        except Exception as exc:
            logger.error(f"Failed to record and evaluate monitoring check for website {website_id}: {exc}", exc_info=True)
            return None
