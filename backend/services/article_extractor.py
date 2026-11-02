import re
import json
import logging
from urllib.parse import urlparse
from typing import Dict, Any, Optional, List
import requests
from bs4 import BeautifulSoup
import trafilatura

from backend.config import config
from backend.models.article import ExtractedArticle
from backend.utils.url_validator import validate_news_url, extract_domain_from_url
from backend.utils.security import is_safe_url
from backend.utils.text_processor import extract_entities

logger = logging.getLogger(__name__)

def extract_article_content(url_input: str) -> ExtractedArticle:
    """
    Extracts structured article data from a news URL.
    Enforces SSRF protection, cleans HTML, extracts metadata,
    entities, author, date, and publisher.
    """
    # 1. URL Validation
    valid, err_msg, normalized_url = validate_news_url(url_input)
    if not valid:
        raise ValueError(err_msg or "Invalid URL format.")

    # 2. SSRF Security Check
    safe, ssrf_err, normalized_url = is_safe_url(normalized_url)
    if not safe:
        raise PermissionError(ssrf_err or "URL blocked by SSRF security shield.")

    domain = extract_domain_from_url(normalized_url)

    # 3. Secure HTTP Fetch
    headers = {
        "User-Agent": config.USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0"
    }

    try:
        response = requests.get(
            normalized_url,
            headers=headers,
            timeout=config.REQUEST_TIMEOUT,
            allow_redirects=True
        )
        response.raise_for_status()
        html = response.text
    except requests.exceptions.Timeout:
        raise TimeoutError(f"Connection to {domain} timed out after {config.REQUEST_TIMEOUT} seconds.")
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Could not retrieve webpage from {domain}: {str(e)}")

    soup = BeautifulSoup(html, "html.parser")
    warnings: List[str] = []

    # 4. Remove Irrelevant / Ad HTML Elements
    for element in soup(["script", "style", "nav", "footer", "aside", "noscript", "svg", "button", "iframe", "form"]):
        element.extract()
    for ad in soup.find_all(class_=re.compile(r"(ad-|advertisement|sponsored|banner|social-share|cookie)", re.I)):
        ad.extract()

    # 5. Extract Metadata (Publisher, Headline, Author, Date)
    # Publisher
    publisher = (
        config.INTERNATIONAL_SOURCES.get(domain) or
        config.INDIAN_SOURCES.get(domain) or
        config.FACT_CHECK_SOURCES.get(domain)
    )
    if not publisher:
        og_site = soup.find("meta", property="og:site_name")
        if og_site and og_site.get("content"):
            publisher = og_site["content"].strip()
        else:
            publisher = domain.split(".")[0].capitalize()

    # Headline
    headline = ""
    # Try OpenGraph
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        headline = og_title["content"].strip()

    # Try JSON-LD
    if not headline:
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, dict):
                    headline = data.get("headline") or data.get("name") or ""
                elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                    headline = data[0].get("headline") or data[0].get("name") or ""
                if headline:
                    break
            except Exception:
                continue

    # Fallback to <title> or <h1>
    if not headline:
        h1 = soup.find("h1")
        if h1 and h1.get_text().strip():
            headline = h1.get_text().strip()
        elif soup.title and soup.title.get_text().strip():
            headline = soup.title.get_text().strip()

    # Clean headline brand suffix (e.g. "Headline - BBC News")
    headline = re.sub(r"\s*[-|]\s*(?:BBC News|Reuters|The Hindu|CNN|NDTV|Times of India).*$", "", headline, flags=re.I).strip()
    if not headline:
        headline = f"News Report from {publisher}"

    # Author
    author = "Unknown"
    author_tag = soup.find("meta", attrs={"name": "author"}) or soup.find("meta", property="article:author")
    if author_tag and author_tag.get("content"):
        author = author_tag["content"].strip()
    else:
        byline = soup.find(class_=re.compile(r"(byline|author-name|contributor)", re.I))
        if byline:
            author = byline.get_text().strip()[:60]

    # Published Date
    published_date = None
    time_tag = soup.find("time")
    if time_tag:
        published_date = time_tag.get("datetime") or time_tag.get_text().strip()
    if not published_date:
        date_meta = (
            soup.find("meta", property="article:published_time") or
            soup.find("meta", attrs={"name": "pubdate"}) or
            soup.find("meta", attrs={"name": "publish-date"}) or
            soup.find("meta", attrs={"name": "date"})
        )
        if date_meta and date_meta.get("content"):
            published_date = date_meta["content"].strip()[:25]

    # 6. Extract Main Body Text (Trafilatura with BeautifulSoup fallback)
    is_live = "/live/" in normalized_url or "live-news" in normalized_url or "liveblog" in normalized_url

    article_text = ""
    try:
        # Trafilatura provides pristine text with boilerplate and ads removed
        trafilatura_text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            no_fallback=False
        )
        if trafilatura_text and len(trafilatura_text.strip()) >= 80:
            article_text = trafilatura_text.strip()
    except Exception as e:
        logger.warning(f"Trafilatura extraction exception: {e}")

    # Fallback to BeautifulSoup if Trafilatura missed content (e.g. on live blogs)
    if not article_text or len(article_text.split()) < 30:
        paragraphs = []
        body_container = soup.find("article") or soup.find("main") or soup.find(class_=re.compile(r"(article-body|story-body|entry-content)", re.I)) or soup
        for p in body_container.find_all(["p", "li"]):
            txt = p.get_text().strip()
            if len(txt) > 30 and not re.search(r"(cookies|copyright|all rights reserved|terms of use)", txt, re.I):
                paragraphs.append(txt)
        if paragraphs:
            article_text = "\n\n".join(paragraphs[:30])

    # Check meta description if body is still sparse
    if not article_text or len(article_text.split()) < 20:
        meta_desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", property="og:description")
        if meta_desc and meta_desc.get("content"):
            article_text = meta_desc["content"].strip()
            warnings.append("Body content extracted from central meta description.")

    if not article_text:
        article_text = headline
        warnings.append("Limited body text found on webpage.")

    if is_live:
        warnings.append("Live blog format detected: extracted central event summary and verified headline.")

    # 7. Entity Extraction (People, Places, Organizations, Numbers, Quotes)
    structured_entities = extract_entities(f"{headline}\n\n{article_text}")
    all_entities = (
        structured_entities["people"][:4] +
        structured_entities["organizations"][:4] +
        structured_entities["locations"][:4]
    )

    # 8. Summary Generation
    summary_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", article_text) if len(s.strip()) > 20]
    summary = " ".join(summary_sentences[:4]) if summary_sentences else article_text[:350]

    return ExtractedArticle(
        url=normalized_url,
        domain=domain,
        publisher=publisher,
        headline=headline,
        author=author,
        published_date=published_date,
        text=article_text,
        summary=summary,
        word_count=len(article_text.split()),
        entities=all_entities,
        structured_entities=structured_entities,
        is_live_blog=is_live,
        warnings=warnings
    )
