import ipaddress
import socket
from urllib.parse import urlparse
from typing import Tuple

BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.88.99.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("255.255.255.255/32"),
    # IPv6 ranges
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

def is_safe_url(url: str) -> Tuple[bool, str, str]:
    """
    Validates a URL against Server-Side Request Forgery (SSRF) risks.
    Returns (is_safe, error_message, cleaned_url).
    """
    if not url or not isinstance(url, str):
        return False, "Empty or invalid URL provided", ""

    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Malformed URL syntax: {str(e)}", ""

    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Prohibited URL scheme: {parsed.scheme}. Only HTTP/HTTPS permitted.", ""

    hostname = parsed.hostname
    if not hostname:
        return False, "URL does not contain a valid domain hostname.", ""

    hostname_lower = hostname.lower()

    # Block localhost aliases
    if hostname_lower in ("localhost", "local", "broadcasthost", "0.0.0.0"):
        return False, "Access to localhost and internal loopback addresses is prohibited.", ""

    # Check port if explicitly specified
    if parsed.port and parsed.port not in (80, 443, 8080):
        return False, f"Non-standard HTTP port {parsed.port} blocked for security.", ""

    # Check if hostname itself is an IP literal
    try:
        ip_obj = ipaddress.ip_address(hostname)
        for blocked_net in BLOCKED_IP_NETWORKS:
            if ip_obj in blocked_net:
                return False, f"URL targets restricted private IP address ({hostname}).", ""
        return True, "", url
    except ValueError:
        pass  # Not an IP literal, it is a domain name

    # Resolve IP address to detect DNS rebinding or private DNS names
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        for family, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            ip_obj = ipaddress.ip_address(ip_str)
            for blocked_net in BLOCKED_IP_NETWORKS:
                if ip_obj in blocked_net:
                    return False, f"URL resolves to restricted private IP range ({ip_str}).", ""
    except (socket.gaierror, socket.timeout):
        # In sandboxed or offline environments DNS can fail; verify domain syntax
        if "." not in hostname or hostname.endswith(".local") or hostname.endswith(".internal"):
            return False, f"Restricted or unresolvable internal domain '{hostname}'.", ""
    except Exception as e:
        return False, f"Host validation failed: {str(e)}", ""

    return True, "", url
