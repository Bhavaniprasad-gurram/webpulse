import pytest
from services.website_service import WebsiteService, ValidationError


def test_valid_urls():
    """Verify standard legitimate public URLs pass SSRF and protocol validation."""
    valid_urls = [
        "https://example.com",
        "http://example.com",
        "https://www.python.org/downloads",
        "https://github.com/torvalds/linux",
    ]
    for url in valid_urls:
        is_safe, err = WebsiteService.validate_ssrf(url)
        assert is_safe is True, f"Expected safe for {url}, got error: {err}"


def test_reject_unsupported_schemes():
    """Verify non-HTTP/HTTPS protocols are rejected."""
    bad_urls = [
        "ftp://files.example.com",
        "file:///etc/passwd",
        "gopher://example.com",
        "javascript:alert(1)",
    ]
    for url in bad_urls:
        is_safe, err = WebsiteService.validate_ssrf(url)
        assert is_safe is False
        assert "Unsupported protocol" in (err or "") or "invalid" in (err or "").lower()


def test_ssrf_rejects_localhost_and_loopback():
    """Verify localhost, 127.0.0.1, and loopback IPs are blocked."""
    loopback_urls = [
        "http://localhost",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:3306",
        "http://[::1]:8080",
    ]
    for url in loopback_urls:
        is_safe, err = WebsiteService.validate_ssrf(url)
        assert is_safe is False
        assert "localhost" in (err or "").lower() or "loopback" in (err or "").lower() or "private" in (err or "").lower()


def test_ssrf_rejects_private_ips_and_cloud_metadata():
    """Verify private RFC 1918 IPs and AWS/GCP cloud metadata endpoints are blocked."""
    internal_urls = [
        "http://10.0.0.1/admin",
        "http://172.16.0.5:8080",
        "http://192.168.1.1/router",
        "http://169.254.169.254/latest/meta-data/",
    ]
    for url in internal_urls:
        is_safe, err = WebsiteService.validate_ssrf(url)
        assert is_safe is False
        assert "private" in (err or "").lower() or "ssrf" in (err or "").lower()


def test_registration_validation_thresholds():
    """Verify boundaries for name, interval, and timeout."""
    # Blank name
    with pytest.raises(ValidationError, match="Website name cannot be blank"):
        WebsiteService.validate_registration_data("", "https://example.com", 60, 10)

    # Interval too low (< 10)
    with pytest.raises(ValidationError, match="Monitoring interval must be between"):
        WebsiteService.validate_registration_data("Test", "https://example.com", 5, 10)

    # Timeout out of bounds (< 1 or > 60)
    with pytest.raises(ValidationError, match="Request timeout must be between"):
        WebsiteService.validate_registration_data("Test", "https://example.com", 60, 0)

    with pytest.raises(ValidationError, match="Request timeout must be between"):
        WebsiteService.validate_registration_data("Test", "https://example.com", 60, 90)
