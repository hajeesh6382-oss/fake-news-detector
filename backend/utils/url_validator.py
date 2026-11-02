import re
from urllib.parse import urlparse
from typing import Tuple, Optional

def validate_news_url(url_str: str) -> Tuple[bool, Optional[str], str]:
    """
    Validates a submitted news URL.
    Returns: (is_valid, error_message, normalized_url)
    """
    if not url_str or not isinstance(url_str, str):
        return False, "URL cannot be empty.", ""

    url = url_str.strip()
    if not re.match(r"^https?:\/\/", url, re.I):
        if "." not in url or " " in url or len(url) < 6:
            return False, f"'{url}' is not a valid web URL or recognizable web address.", ""
        url = "https://" + url

    try:
        parsed = urlparse(url)
        if not parsed.scheme or parsed.scheme.lower() not in ("http", "https"):
            return False, "URL scheme must be HTTP or HTTPS.", ""
        if not parsed.hostname:
            return False, "URL is missing a valid domain hostname.", ""
        if "." not in parsed.hostname and parsed.hostname != "localhost":
            return False, "Invalid domain hostname format.", ""
        return True, None, url
    except Exception as e:
        return False, f"Could not parse URL: {str(e)}", ""

def extract_domain_from_url(url_str: str) -> str:
    """Extracts lowercase clean domain hostname."""
    try:
        parsed = urlparse(url_str.strip())
        host = parsed.hostname or ""
        return host.lower().replace("www.", "")
    except Exception:
        return ""
