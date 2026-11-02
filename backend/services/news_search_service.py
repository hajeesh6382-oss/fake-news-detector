import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
import logging
from typing import List, Dict, Any, Optional
import httpx
import asyncio

from backend.config import config
from backend.models.evidence import EvidenceSource
from backend.utils.text_processor import compute_tfidf_similarity, is_syndicated_reprint

logger = logging.getLogger(__name__)

# 1-Hour In-Memory Cache (search_key -> (timestamp, data))
SEARCH_CACHE: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
CACHE_TTL = 3600  # 1 hour

def get_clean_search_terms(headline: str, entities: List[str] = None) -> str:
    """Extracts high-signal keywords and entity names for search queries."""
    clean = re.sub(r"[^\w\s-]", " ", headline)
    words = clean.split()
    stopwords = {
        "a", "an", "the", "in", "on", "at", "to", "for", "of", "with", "by", "from",
        "and", "or", "is", "are", "was", "were", "be", "been", "has", "have", "had",
        "say", "says", "said", "after", "over", "under", "into", "live", "follow", "updates", "breaking"
    }
    keywords = [w for w in words if w.lower() not in stopwords and len(w) > 2]
    
    # If specific entities (people, places, orgs) are passed, prioritize them
    if entities:
        for ent in entities[:2]:
            if ent and ent not in keywords:
                keywords.insert(0, ent)

    return " ".join(keywords[:6])

async def fetch_google_news_rss(client: httpx.AsyncClient, query: str, platform_hint: str = "") -> List[Dict[str, Any]]:
    """
    Fetches real news articles from Google News RSS index for a given event query.
    Optionally filters by site (e.g. site:bbc.com).
    """
    encoded_q = urllib.parse.quote(query.strip())
    url = f"https://news.google.com/rss/search?q={encoded_q}&hl=en-US&gl=US&ceid=US:en"
    results = []

    try:
        resp = await client.get(url, timeout=7.0, follow_redirects=True)
        if resp.status_code == 200:
            root = ET.fromstring(resp.text)
            for item in root.findall(".//item")[:5]:
                title = item.find("title").text if item.find("title") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                source_elem = item.find("source")
                source_name = source_elem.text if source_elem is not None else platform_hint or "News Wire"

                if title and link:
                    # Clean source suffix from title
                    clean_title = re.sub(r"\s*-\s*[^-]+$", "", title).strip()
                    results.append({
                        "platform": source_name,
                        "title": clean_title,
                        "link": link,
                        "date": pub_date,
                        "source_type": "Google News RSS"
                    })
    except Exception as e:
        logger.debug(f"Google News RSS query failed for '{query}': {e}")

    return results

async def fetch_gdelt_articles(client: httpx.AsyncClient, query: str) -> List[Dict[str, Any]]:
    """
    Queries the GDELT 2.0 Doc API (Global Database of Events, Language, and Tone).
    Provides free, public, world-scale event verification.
    """
    encoded_q = urllib.parse.quote(query.strip())
    url = f"https://api.gdeltproject.org/api/v2/doc/doc?query={encoded_q}&mode=artlist&format=json&maxrecords=5&sort=datedesc"
    results = []

    try:
        resp = await client.get(url, timeout=7.0, follow_redirects=True)
        if resp.status_code == 200:
            data = resp.json()
            articles = data.get("articles", [])
            for art in articles:
                title = art.get("title", "")
                link = art.get("url", "")
                domain = art.get("domain", "")
                date_str = art.get("seendate", "")
                if title and link:
                    results.append({
                        "platform": domain or "GDELT Wire",
                        "title": title,
                        "link": link,
                        "date": date_str,
                        "source_type": "GDELT"
                    })
    except Exception as e:
        logger.debug(f"GDELT query exception: {e}")

    return results

async def fetch_newsapi_articles(client: httpx.AsyncClient, query: str) -> List[Dict[str, Any]]:
    """Queries NewsAPI if key is configured."""
    if not config.NEWS_API_KEY:
        return []

    encoded_q = urllib.parse.quote(query.strip())
    url = f"https://newsapi.org/v2/everything?q={encoded_q}&pageSize=5&sortBy=relevancy&apiKey={config.NEWS_API_KEY}"
    results = []

    try:
        resp = await client.get(url, timeout=7.0)
        if resp.status_code == 200:
            data = resp.json()
            for art in data.get("articles", []):
                results.append({
                    "platform": art.get("source", {}).get("name", "NewsAPI"),
                    "title": art.get("title", ""),
                    "link": art.get("url", ""),
                    "date": art.get("publishedAt", ""),
                    "source_type": "NewsAPI"
                })
    except Exception as e:
        logger.debug(f"NewsAPI error: {e}")

    return results

async def search_cross_platform_news(
    headline: str,
    entities: List[str] = None,
    primary_domain: str = "",
    primary_url: str = ""
) -> List[Dict[str, Any]]:
    """
    Asynchronously queries:
    - Google News RSS (broad event query)
    - Specific International Outlets (BBC, Reuters, AP, The Hindu, CNN)
    - GDELT Event Index
    - NewsAPI (if configured)
    Returns list of discovered news reports reporting on the same event.
    """
    search_terms = get_clean_search_terms(headline, entities)
    if not search_terms:
        return []

    # Check Cache
    now = time.time()
    cache_key = search_terms.lower()
    if cache_key in SEARCH_CACHE:
        cached_time, cached_data = SEARCH_CACHE[cache_key]
        if now - cached_time < CACHE_TTL:
            return cached_data

    headers = {"User-Agent": config.USER_AGENT}
    all_results: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(headers=headers, timeout=8.0) as client:
        # Launch parallel search tasks across providers
        tasks = [
            fetch_google_news_rss(client, search_terms),
            fetch_google_news_rss(client, f"{search_terms} site:bbc.com", "BBC News"),
            fetch_google_news_rss(client, f"{search_terms} site:reuters.com", "Reuters"),
            fetch_google_news_rss(client, f"{search_terms} site:thehindu.com", "The Hindu"),
            fetch_google_news_rss(client, f"{search_terms} site:apnews.com", "Associated Press"),
            fetch_gdelt_articles(client, search_terms),
            fetch_newsapi_articles(client, search_terms)
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        seen_links = set()
        if primary_url:
            seen_links.add(primary_url)

        for res in responses:
            if isinstance(res, list):
                for item in res:
                    link = item.get("link", "")
                    title = item.get("title", "")
                    if not link or link in seen_links:
                        continue
                    seen_links.add(link)

                    # Compute semantic similarity to original headline
                    sim = compute_tfidf_similarity(headline, title)
                    item["similarity"] = sim
                    all_results.append(item)

    # Sort by similarity descending
    all_results.sort(key=lambda x: x.get("similarity", 0.0), reverse=True)

    # Cache results
    SEARCH_CACHE[cache_key] = (now, all_results)

    return all_results
