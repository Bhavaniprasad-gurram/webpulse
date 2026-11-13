import socket
import ipaddress
from urllib.parse import urlparse
from typing import Tuple, Optional, Dict, Any, List
from database.connection import get_db
from database.models import Website
from repositories.website_repository import WebsiteRepository


class ValidationError(Exception):
    """Custom exception raised for validation failures."""
    pass


class WebsiteService:
    """Service handling website business logic, input validation, and SSRF security controls."""

    # Disallowed cloud metadata & loopback IPs
    BLOCKED_IPS = {"169.254.169.254"}

    @classmethod
    def _is_disallowed_ip(cls, ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        """Check if an IP address belongs to internal, loopback, link-local, or cloud metadata ranges."""
        if str(ip) in cls.BLOCKED_IPS:
            return True
        if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
            return True
        return False

    @classmethod
    def validate_ssrf(cls, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that the target URL does not resolve to private, loopback,
        link-local, or cloud metadata network destinations.
        """
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False, f"Unsupported protocol '{parsed.scheme}'. Only http and https are allowed."

            hostname = parsed.hostname
            if not hostname:
                return False, "Target URL missing a valid domain or host name."

            # Block raw localhost string
            if hostname.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
                return False, "Access to localhost and loopback interfaces is strictly prohibited."

            # Check if hostname directly represents an IP
            try:
                ip = ipaddress.ip_address(hostname)
                if cls._is_disallowed_ip(ip):
                    return False, f"Access to private/internal network IP {ip} is prohibited (SSRF protection)."
            except ValueError:
                # Not a literal IP address, resolve hostname via DNS
                try:
                    addr_info = socket.getaddrinfo(hostname, None)
                    for entry in addr_info:
                        resolved_ip_str = entry[4][0]
                        resolved_ip = ipaddress.ip_address(resolved_ip_str)
                        if cls._is_disallowed_ip(resolved_ip):
                            return False, (
                                f"Host '{hostname}' resolves to private/internal IP {resolved_ip_str} "
                                f"(SSRF protection)."
                            )
                except socket.gaierror:
                    # DNS resolution failure will be captured properly during monitoring check
                    pass

            return True, None
        except Exception as e:
            return False, f"URL validation error: {str(e)}"

    @classmethod
    def validate_registration_data(
        cls, name: str, url: str, interval: int, timeout: int, existing_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Validate all input fields for adding or editing a website."""
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValidationError("Website name cannot be blank.")
        if len(cleaned_name) > 150:
            raise ValidationError("Website name cannot exceed 150 characters.")

        cleaned_url = url.strip()
        if not cleaned_url:
            raise ValidationError("Website URL cannot be blank.")
        if not (cleaned_url.startswith("http://") or cleaned_url.startswith("https://")):
            raise ValidationError("URL must begin with http:// or https://")

        # SSRF checks
        is_safe, ssrf_err = cls.validate_ssrf(cleaned_url)
        if not is_safe:
            raise ValidationError(ssrf_err or "URL failed SSRF validation.")

        if not (10 <= interval <= 86400):
            raise ValidationError("Monitoring interval must be between 10 seconds and 86,400 seconds (24 hours).")

        if not (1 <= timeout <= 60):
            raise ValidationError("Request timeout must be between 1 and 60 seconds.")

        # Check duplicate URL
        with get_db() as session:
            existing = WebsiteRepository.get_by_url(session, cleaned_url)
            if existing and existing.id != existing_id:
                raise ValidationError(f"A monitored website with URL '{cleaned_url}' is already registered ('{existing.name}').")

        return {
            "name": cleaned_name,
            "url": cleaned_url,
            "monitoring_interval_seconds": interval,
            "timeout_seconds": timeout,
        }

    @classmethod
    def register_website(cls, name: str, url: str, interval: int = 60, timeout: int = 10,
                          description: Optional[str] = None, user_id: Optional[int] = None) -> Website:
        """Register a new website target for monitoring."""
        data = cls.validate_registration_data(name, url, interval, timeout)
        data["description"] = description
        data["user_id"] = user_id
        data["is_active"] = True

        with get_db() as session:
            website = WebsiteRepository.create(session, data)
            # Fetch with eager loading or return detached object data
            website_id = website.id

        return cls.get_website(website_id)

    @classmethod
    def update_website(cls, website_id: int, name: str, url: str, interval: int, timeout: int,
                       is_active: bool, description: Optional[str] = None) -> Optional[Website]:
        """Update existing website settings."""
        data = cls.validate_registration_data(name, url, interval, timeout, existing_id=website_id)
        data["is_active"] = is_active
        data["description"] = description

        with get_db() as session:
            website = WebsiteRepository.update(session, website_id, data)
            return website

    @classmethod
    def delete_website(cls, website_id: int) -> bool:
        """Permanently remove website and cascade its history."""
        with get_db() as session:
            return WebsiteRepository.delete(session, website_id)

    @classmethod
    def toggle_active(cls, website_id: int) -> Optional[Website]:
        """Pause or resume monitoring for a website."""
        with get_db() as session:
            return WebsiteRepository.toggle_active(session, website_id)

    @classmethod
    def get_website(cls, website_id: int) -> Optional[Website]:
        with get_db() as session:
            return WebsiteRepository.get_by_id(session, website_id)

    @classmethod
    def list_websites(cls, include_inactive: bool = True) -> List[Website]:
        with get_db() as session:
            return WebsiteRepository.get_all(session, include_inactive=include_inactive)
