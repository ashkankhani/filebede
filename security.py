"""Security utilities for URL validation and SSRF protection."""
import ipaddress
import re
from urllib.parse import urlparse


# Private IP ranges to block
PRIVATE_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("10.0.0.0/8"),        # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),     # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),    # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 private
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
]

# Metadata endpoints
BLOCKED_HOSTS = [
    "169.254.169.254",  # AWS metadata
    "metadata.google.internal",  # GCP metadata
    "169.254.169.254.nip.io",  # Alternative
]


def is_valid_url(url: str) -> bool:
    """Validate URL scheme and format."""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ["http", "https"] and bool(parsed.netloc)
    except Exception:
        return False


def is_private_ip(hostname: str) -> bool:
    """Check if hostname resolves to private IP."""
    try:
        ip = ipaddress.ip_address(hostname)
        return any(ip in network for network in PRIVATE_RANGES)
    except ValueError:
        return False


def is_safe_url(url: str) -> tuple[bool, str]:
    """Check if URL is safe to download from.
    
    Returns:
        (is_safe, reason)
    """
    if not is_valid_url(url):
        return False, "Invalid URL format"
    
    parsed = urlparse(url)
    hostname = parsed.hostname
    
    if not hostname:
        return False, "No hostname"
    
    # Check blocked hosts
    if hostname in BLOCKED_HOSTS:
        return False, "Blocked metadata endpoint"
    
    # Check for localhost variations
    if hostname.lower() in ["localhost", "0.0.0.0"]:
        return False, "Localhost blocked"
    
    # Check for private IPs
    if is_private_ip(hostname):
        return False, "Private IP blocked"
    
    # Check for common bypass attempts
    if re.search(r"\\d+\\.\\d+\\.\\d+\\.\\d+", hostname):
        # IP address in hostname
        if is_private_ip(hostname):
            return False, "IP address blocked"
    
    return True, "OK"
