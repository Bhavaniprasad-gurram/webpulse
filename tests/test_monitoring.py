from unittest.mock import patch, MagicMock
import requests
from database.models import Website
from services.monitoring_service import MonitoringService


def test_monitoring_successful_200():
    """Verify HTTP 200 response evaluates to operational."""
    site = Website(id=1, name="Example", url="https://example.com", timeout_seconds=10)
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.reason = "OK"

    with patch("requests.get", return_value=mock_response):
        result = MonitoringService.check_website(site)
        assert result.is_available is True
        assert result.http_status_code == 200
        assert result.error_type is None
        assert result.response_time_ms is not None


def test_monitoring_redirect_301_operational():
    """Verify HTTP 301 redirect is treated as operational."""
    site = Website(id=2, name="Redirect Site", url="http://example.com", timeout_seconds=10)
    
    mock_response = MagicMock()
    mock_response.status_code = 301
    mock_response.reason = "Moved Permanently"

    with patch("requests.get", return_value=mock_response):
        result = MonitoringService.check_website(site)
        assert result.is_available is True
        assert result.http_status_code == 301


def test_monitoring_client_error_404():
    """Verify HTTP 404 is classified as downtime."""
    site = Website(id=3, name="Broken Page", url="https://example.com/missing", timeout_seconds=10)
    
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.reason = "Not Found"

    with patch("requests.get", return_value=mock_response):
        result = MonitoringService.check_website(site)
        assert result.is_available is False
        assert result.http_status_code == 404
        assert result.error_type == "HTTP_404_CLIENT_ERROR"


def test_monitoring_server_error_500():
    """Verify HTTP 500 is classified as downtime."""
    site = Website(id=4, name="Server Crash", url="https://api.example.com", timeout_seconds=10)
    
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.reason = "Internal Server Error"

    with patch("requests.get", return_value=mock_response):
        result = MonitoringService.check_website(site)
        assert result.is_available is False
        assert result.http_status_code == 500
        assert result.error_type == "HTTP_500_SERVER_ERROR"


def test_monitoring_connect_timeout():
    """Verify connection timeout is caught and categorized."""
    site = Website(id=5, name="Slow Site", url="https://slow.example.com", timeout_seconds=5)

    with patch("requests.get", side_effect=requests.exceptions.ConnectTimeout()):
        result = MonitoringService.check_website(site)
        assert result.is_available is False
        assert result.error_type == "CONNECTION_TIMEOUT"
        assert result.http_status_code is None


def test_monitoring_ssl_error():
    """Verify SSL certificate expiration or failure is classified."""
    site = Website(id=6, name="Bad SSL", url="https://expired-ssl.example.com", timeout_seconds=10)

    with patch("requests.get", side_effect=requests.exceptions.SSLError("CERTIFICATE_VERIFY_FAILED")):
        result = MonitoringService.check_website(site)
        assert result.is_available is False
        assert result.error_type == "SSL_ERROR"


def test_monitoring_dns_error():
    """Verify DNS resolution failure is classified."""
    site = Website(id=7, name="Nonexistent", url="https://does-not-exist-xyz123.org", timeout_seconds=10)

    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("Name or service not known")):
        result = MonitoringService.check_website(site)
        assert result.is_available is False
        assert result.error_type == "DNS_ERROR"
