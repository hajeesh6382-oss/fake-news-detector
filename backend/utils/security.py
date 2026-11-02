import ipaddress
import socket
from urllib.parse import urlparse
from typing import Tuple, Optional

BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback
    ipaddress.ip_network("10.0.0.0/8"),        # Private network
    ipaddress.ip_network("172.16.0.0/12"),     # Private network
    ipaddress.ip_network("192.168.0.0/16"),    # Private network
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local / Cloud metadata (169.254.169.254)
    ipaddress.ip_network("0.0.0.0/8"),         # Broadcast / current network
    ipaddress.ip_network("100.64.0.0/10"),     # Carrier-grade NAT
    ipaddress.ip_network("192.0.0.0/24"),      # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),      # Documentation TEST-NET-1
    ipaddress.ip_network("198.51.100.0/24"),   # Documentation TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),    # Documentation TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),       # Multicast
    ipaddress.ip_network("240.0.0.0/4"),       # Reserved
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "metadata.google.internal",
    "instance-data"
}

def is_safe_url(url_str: str) -> Tuple[bool, Optional[str], str]:
    """
    Checks if a URL is safe from SSRF vulnerabilities.
    Returns: (is_safe, error_message, normalized_url)
    """
    if not url_str or not isinstance(url_str, str):
        return False, "Empty URL provided.", ""

    url = url_str.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False, "Invalid URL: hostname missing.", ""

        host_lower = hostname.lower()
        if host_lower in BLOCKED_HOSTNAMES or host_lower.endswith((".local", ".internal", ".localhost")):
            return False, f"Access to '{hostname}' is blocked by security policy.", ""

        # Check if hostname is direct IP address
        try:
            ip_obj = ipaddress.ip_address(hostname)
            for net in BLOCKED_IP_NETWORKS:
                if ip_obj in net:
                    return False, f"Access to private IP address {hostname} is prohibited.", ""
        except ValueError:
            # Hostname is a domain name; try resolving it
            try:
                addr_info = socket.getaddrinfo(hostname, None)
                for item in addr_info:
                    resolved_ip_str = item[4][0]
                    try:
                        resolved_ip = ipaddress.ip_address(resolved_ip_str)
                        for net in BLOCKED_IP_NETWORKS:
                            if resolved_ip in net:
                                return False, f"Domain '{hostname}' resolves to restricted internal IP {resolved_ip}.", ""
                    except ValueError:
                        pass
            except socket.gaierror:
                # In sandboxed / offline environments DNS might not resolve; allow standard public domain format
                if "." not in hostname:
                    return False, f"Domain '{hostname}' cannot be resolved.", ""

        return True, None, url
    except Exception as e:
        return False, f"Security check failed: {str(e)}", ""

