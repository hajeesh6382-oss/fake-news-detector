import re
from urllib.parse import urlparse
from typing import Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
from backend.config import config
from backend.extractors.security import is_safe_url

def extract_article_from_url(url: str) -> Dict[str, Any]:
    """
    Safely extracts article title, text, metadata, and publication date from a news URL.
    """
    safe, err, normalized_url = is_safe_url(url)
    if not safe:
        raise ValueError(f"Security validation error: {err}")

    parsed = urlparse(normalized_url)
    domain = parsed.hostname.lower().replace("www.", "") if parsed.hostname else ""

    headers = {
        "User-Agent": config.USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "close"
    }

    try:
        response = requests.get(
            normalized_url,
            headers=headers,
            timeout=config.REQUEST_TIMEOUT,
            allow_redirects=True
        )
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise TimeoutError(f"Connection to {domain} timed out after {config.REQUEST_TIMEOUT}s.")
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Could not retrieve webpage: {str(e)}")

    html = response.text
    soup = BeautifulSoup(html, "html.parser")

    # 1. Extract Title
    title = ""
    og_title = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "twitter:title"})
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    elif soup.title and soup.title.string:
        title = soup.title.string.strip()
    elif soup.find("h1"):
        title = soup.find("h1").get_text().strip()

    # Clean up standard site suffixes from title (e.g., " - BBC News", " | The Hindu")
    title = re.sub(r"\s*[-|–]\s*(BBC News|The Hindu|CNN|Reuters|Times of India|NDTV|The Guardian).*$", "", title, flags=re.I).strip()

    # 2. Extract Publication Date
    published_date = None
    date_meta = (
        soup.find("meta", property="article:published_time") or
        soup.find("meta", attrs={"name": "date"}) or
        soup.find("meta", attrs={"name": "pubdate"}) or
        soup.find("meta", attrs={"name": "publish-date"}) or
        soup.find("meta", property="og:published_time")
    )
    if date_meta and date_meta.get("content"):
        published_date = date_meta["content"].strip()
    else:
        time_tag = soup.find("time")
        if time_tag:
            published_date = time_tag.get("datetime") or time_tag.get_text().strip()

    # 3. Extract Author / Source
    author = ""
    author_meta = soup.find("meta", attrs={"name": "author"}) or soup.find("meta", property="article:author")
    if author_meta and author_meta.get("content"):
        author = author_meta["content"].strip()

    site_name = domain
    site_meta = soup.find("meta", property="og:site_name")
    if site_meta and site_meta.get("content"):
        site_name = site_meta["content"].strip()

    # 4. Extract Main Article Body
    # Remove scripts, styles, forms, and navigation tags
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "svg", "form", "button"]):
        tag.decompose()

    # Look for article container
    article_elem = (
        soup.find("article") or
        soup.find("div", class_=re.compile(r"article[-_]?(body|content|text)", re.I)) or
        soup.find("main") or
        soup.body
    )

    paragraphs = []
    if article_elem:
        for p in article_elem.find_all("p"):
            p_text = p.get_text().strip()
            # Filter out very short UI texts or social share hints
            if len(p_text) > 35 and not re.search(r"^(read more|follow us|subscribe|share this|copyright|sign up)", p_text, re.I):
                paragraphs.append(p_text)

    full_text = "\n\n".join(paragraphs).strip()

    # Fallback to meta description if body is empty or paywalled
    if not full_text:
        meta_desc = (
            soup.find("meta", attrs={"name": "description"}) or
            soup.find("meta", property="og:description")
        )
        if meta_desc and meta_desc.get("content"):
            full_text = meta_desc["content"].strip()

    if not title and not full_text:
        raise ValueError(f"Could not extract meaningful article content or headline from {domain}.")

    # Summary: first 2-3 paragraphs or ~400 chars
    summary = "\n\n".join(paragraphs[:3]) if paragraphs else full_text[:400]

    # Domain reputation check
    is_trusted = any(td in domain for td in config.TRUSTED_DOMAINS)
    is_suspicious = any(domain.endswith(tld) for tld in config.SUSPICIOUS_TLDS)

    return {
        "url": normalized_url,
        "domain": domain,
        "site_name": site_name,
        "title": title or "Untitled Article",
        "published_date": published_date,
        "author": author,
        "text": full_text,
        "summary": summary,
        "word_count": len(full_text.split()),
        "is_trusted_domain": is_trusted,
        "is_suspicious_domain": is_suspicious
    }
