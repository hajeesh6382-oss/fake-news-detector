import re
import json
from urllib.parse import urlparse
from typing import Dict, Any, Optional, List
import requests
from bs4 import BeautifulSoup
from backend.config import config
from backend.extractors.security import is_safe_url

def extract_article_from_url(url: str) -> Dict[str, Any]:
    """
    Safely extracts article title, text, metadata, and publication date from a news URL.
    Handles standard articles, live coverage / live blogs (like BBC /news/live/),
    and falls back to OpenGraph, Twitter Cards, JSON-LD, and meta tags.
    """
    warnings: List[str] = []

    safe, err, normalized_url = is_safe_url(url)
    if not safe:
        raise ValueError(f"Security validation error: {err}")

    parsed = urlparse(normalized_url)
    domain = parsed.hostname.lower().replace("www.", "") if parsed.hostname else ""

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
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
        raise ConnectionError(f"Could not retrieve webpage from {domain}: {str(e)}")

    html = response.text
    soup = BeautifulSoup(html, "html.parser")

    # 1. Extract JSON-LD Metadata if present
    json_ld_headline = ""
    json_ld_desc = ""
    json_ld_date = ""
    json_ld_author = ""

    for s in soup.find_all("script", type="application/ld+json"):
        if s.string:
            try:
                data = json.loads(s.string)
                if isinstance(data, list):
                    data = data[0] if data else {}
                if isinstance(data, dict):
                    # Check @graph if nested
                    if "@graph" in data and isinstance(data["@graph"], list):
                        for item in data["@graph"]:
                            if item.get("@type") in ("NewsArticle", "Article", "LiveBlogPosting"):
                                data = item
                                break

                    json_ld_headline = data.get("headline", "") or data.get("name", "")
                    json_ld_desc = data.get("description", "")
                    json_ld_date = data.get("datePublished", "") or data.get("dateModified", "")
                    author_val = data.get("author", "")
                    if isinstance(author_val, dict):
                        json_ld_author = author_val.get("name", "")
                    elif isinstance(author_val, list) and author_val:
                        json_ld_author = author_val[0].get("name", "") if isinstance(author_val[0], dict) else str(author_val[0])
                    elif isinstance(author_val, str):
                        json_ld_author = author_val
            except Exception:
                pass

    # 2. Extract Title (OpenGraph, Twitter, JSON-LD, <title>, h1)
    title = ""
    og_title = (
        soup.find("meta", property="og:title") or
        soup.find("meta", attrs={"name": "twitter:title"}) or
        soup.find("meta", attrs={"name": "title"})
    )
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    elif json_ld_headline:
        title = json_ld_headline.strip()
    elif soup.title and soup.title.string:
        title = soup.title.string.strip()
    elif soup.find("h1"):
        title = soup.find("h1").get_text().strip()

    # Clean up standard site suffixes from title (e.g., " - BBC News", " - follow live")
    title = re.sub(r"\s*[-|–]\s*(BBC News|The Hindu|CNN|Reuters|Times of India|NDTV|The Guardian|follow live).*$", "", title, flags=re.I).strip()

    # 3. Extract Description / Meta Summary
    description = ""
    og_desc = (
        soup.find("meta", property="og:description") or
        soup.find("meta", attrs={"name": "description"}) or
        soup.find("meta", attrs={"name": "twitter:description"})
    )
    if og_desc and og_desc.get("content"):
        description = og_desc["content"].strip()
    elif json_ld_desc:
        description = json_ld_desc.strip()

    # 4. Extract Publication Date
    published_date = json_ld_date
    if not published_date:
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

    # Format date string
    if published_date and len(published_date) >= 10:
        published_date = published_date[:10]
    else:
        published_date = "Recently Published"

    # 5. Extract Author / Publisher
    author = json_ld_author
    if not author:
        author_meta = soup.find("meta", attrs={"name": "author"}) or soup.find("meta", property="article:author")
        if author_meta and author_meta.get("content"):
            author = author_meta["content"].strip()

    publisher = domain
    site_meta = soup.find("meta", property="og:site_name")
    if site_meta and site_meta.get("content"):
        publisher = site_meta["content"].strip()
    elif "bbc" in domain:
        publisher = "BBC News"
    elif "thehindu" in domain:
        publisher = "The Hindu"
    elif "reuters" in domain:
        publisher = "Reuters"
    elif "timesofindia" in domain:
        publisher = "Times of India"

    # 6. Detect Live Page
    is_live_page = "/live/" in normalized_url or "live" in normalized_url.lower().split("/")
    if is_live_page:
        warnings.append("Live blog format detected: extracted central event summary and verified headline.")

    # 7. Extract Body Paragraphs
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "svg", "form", "button"]):
        tag.decompose()

    article_elem = (
        soup.find("article") or
        soup.find("div", class_=re.compile(r"article[-_]?(body|content|text)", re.I)) or
        soup.find("div", class_=re.compile(r"live[-_]?event", re.I)) or
        soup.find("main") or
        soup.body
    )

    paragraphs = []
    if article_elem:
        for p in article_elem.find_all("p"):
            p_text = p.get_text().strip()
            if len(p_text) > 30 and not re.search(r"^(read more|follow us|subscribe|share this|copyright|sign up)", p_text, re.I):
                paragraphs.append(p_text)

    full_text = "\n\n".join(paragraphs).strip()

    # Fallback if body text is minimal (e.g. live blogs or multimedia pages)
    if not full_text or len(full_text.split()) < 20:
        if description:
            full_text = f"{title}. {description}"
            warnings.append("Body text extracted from verified meta description (multimedia/live page format).")
        else:
            full_text = title

    # Summary
    summary = "\n\n".join(paragraphs[:3]) if len(paragraphs) >= 2 else (description or full_text[:400])

    # If title still empty, fallback to URL slug
    if not title or len(title) < 5:
        slug_parts = parsed.pathname.split("/")
        candidate = [s for s in slug_parts if len(s) > 3 and not s.isdigit()]
        if candidate:
            title = candidate[-1].replace("-", " ").replace("_", " ").title()
        else:
            title = f"News Coverage from {publisher}"
        warnings.append("Headline derived from URL identifier.")

    is_trusted = any(td in domain for td in config.TRUSTED_DOMAINS)
    is_suspicious = any(domain.endswith(tld) for tld in config.SUSPICIOUS_TLDS)

    return {
        "url": normalized_url,
        "domain": domain,
        "publisher": publisher,
        "title": title,
        "headline": title,
        "published_date": published_date,
        "author": author,
        "text": full_text,
        "summary": summary,
        "word_count": len(full_text.split()),
        "is_trusted_domain": is_trusted,
        "is_suspicious_domain": is_suspicious,
        "warnings": warnings,
        "is_live_page": is_live_page
    }
