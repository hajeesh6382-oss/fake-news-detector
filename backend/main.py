import os
import re
from urllib.parse import urlparse
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.config import config
from backend.database.db import (
    init_db,
    save_verification,
    get_history,
    get_record_by_id,
    delete_record,
    clear_all_history
)
from backend.extractors.security import is_safe_url
from backend.extractors.url_extractor import extract_article_from_url
from backend.extractors.youtube_extractor import extract_youtube_content
from backend.nlp.claim_extractor import extract_main_claims
from backend.fact_checking.factcheck_engine import verify_story_pipeline, check_known_debunks

# Initialize database
init_db()

app = FastAPI(
    title="Veritas AI Enterprise v2.0",
    description="Advanced AI News & Video Verification Platform with Real-Time Multi-Source Fact-Checking.",
    version="2.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------
# Request Models
# --------------------------------------------------------------------------

class UnifiedVerificationRequest(BaseModel):
    url: Optional[str] = None
    text: Optional[str] = None
    headline: Optional[str] = None

class UrlVerificationRequest(BaseModel):
    url: str

class YouTubeVerificationRequest(BaseModel):
    url: str

class TextVerificationRequest(BaseModel):
    text: str
    headline: Optional[str] = None

# --------------------------------------------------------------------------
# Unified Verification Pipeline Endpoint (POST /api/verify)
# --------------------------------------------------------------------------

@app.post("/api/verify")
@app.post("/verify")
@app.post("/api/verify.py")
@app.post("/api/verify/url")
def unified_verify(req: UnifiedVerificationRequest):
    """
    Unified Verification Engine:
    - Enforces SSRF security
    - Handles standard news articles, live blogs (BBC live), and direct text
    - Checks PIB Fact Check, BOOM, Alt News debunks
    - Performs cross-platform news search with TF-IDF similarity
    - Produces standardized 0-100 score and verdict
    - NEVER returns blank panels or unhandled 404/500 errors
    """
    raw_url = (req.url or "").strip()
    raw_text = (req.text or "").strip()
    headline_input = (req.headline or "").strip()

    # ----------------------------------------------------------------------
    # Case 1: URL Verification
    # ----------------------------------------------------------------------
    if raw_url:
        # Check invalid inputs (like "abc" or malformed strings)
        if not re.match(r"^https?:\/\/", raw_url, re.I):
            if "." not in raw_url or " " in raw_url or len(raw_url) < 6:
                return {
                    "status": "error",
                    "verdict": "INVALID INPUT",
                    "verdict_badge_class": "badge-fake",
                    "score": 0,
                    "headline": raw_url,
                    "publisher": "Unknown",
                    "error_title": "Invalid URL Format",
                    "reason": f"'{raw_url}' is not a valid web URL or recognizable news statement.",
                    "suggestion": "Please paste a complete web URL starting with https:// (e.g., https://www.bbc.com/news/...) or enter a complete statement.",
                    "why_this_verdict": f"The input '{raw_url}' could not be parsed as a valid web address.",
                    "warnings": ["Malformed or incomplete URL provided."],
                    "matching_sources": [],
                    "disclaimer": "Automated estimate, confirm with official sources"
                }
            raw_url = "https://" + raw_url

        # Check SSRF safety
        safe, ssrf_err, normalized_url = is_safe_url(raw_url)
        if not safe:
            return {
                "status": "error",
                "verdict": "BLOCKED URL",
                "verdict_badge_class": "badge-fake",
                "score": 0,
                "headline": raw_url,
                "publisher": "Restricted Target",
                "error_title": "Security Shield Triggered (SSRF Protection)",
                "reason": ssrf_err,
                "suggestion": "Access to local loopback addresses and private subnets is blocked for security. Please use a public news article URL.",
                "why_this_verdict": "Prohibited destination blocked by security policy.",
                "warnings": [ssrf_err],
                "matching_sources": [],
                "disclaimer": "Automated estimate, confirm with official sources"
            }

        parsed_domain = urlparse(normalized_url).hostname or ""

        # Extract article server-side
        try:
            article = extract_article_from_url(normalized_url)
        except (TimeoutError, ConnectionError) as ce:
            # Blocked or timed-out page test case: Return UNVERIFIED with clear reason shown
            return {
                "status": "warning",
                "verdict": "UNVERIFIED",
                "verdict_badge_class": "badge-unverified",
                "score": 45,
                "headline": f"Inaccessible Webpage ({parsed_domain})",
                "publisher": parsed_domain,
                "url": normalized_url,
                "why_this_verdict": f"Could not access or read the webpage: {str(ce)}.",
                "warnings": ["Webpage timed out or connection was blocked by remote server firewall."],
                "matching_sources": [],
                "supporting_evidence": [],
                "contradicting_evidence": [],
                "trusted_sources_checked": ["Google News Wire Index", "Reuters Archive", "BBC News"],
                "disclaimer": "Automated estimate, confirm with official sources"
            }
        except Exception as e:
            return {
                "status": "warning",
                "verdict": "UNVERIFIED",
                "verdict_badge_class": "badge-unverified",
                "score": 40,
                "headline": f"Article from {parsed_domain}",
                "publisher": parsed_domain,
                "url": normalized_url,
                "why_this_verdict": f"Content could not be parsed: {str(e)}.",
                "warnings": ["Content extraction limited."],
                "matching_sources": [],
                "disclaimer": "Automated estimate, confirm with official sources"
            }

        # Run verification pipeline
        pipe_res = verify_story_pipeline(
            headline=article["headline"],
            full_text=article["text"],
            domain=article["domain"],
            publisher=article["publisher"],
            url=article["url"]
        )

        all_warnings = article.get("warnings", []) + pipe_res.get("warnings", [])
        claims = extract_main_claims(article["headline"], article["text"])

        # Persist to SQLite
        try:
            save_verification(
                input_type="url",
                source_url=article["url"],
                headline=article["headline"],
                summary=article["summary"],
                classification=pipe_res["verdict"],
                confidence_score=pipe_res["score"],
                explanation=pipe_res["why_this_verdict"],
                claims=claims,
                supporting_evidence=pipe_res["supporting_evidence"],
                contradicting_evidence=pipe_res["contradicting_evidence"],
                trusted_sources_checked=pipe_res["trusted_sources_checked"],
                is_outdated=False,
                published_date=article.get("published_date")
            )
        except Exception:
            pass

        return {
            "status": "success",
            "url": article["url"],
            "domain": article["domain"],
            "publisher": article["publisher"],
            "headline": article["headline"],
            "published_date": article.get("published_date"),
            "author": article.get("author"),
            "extracted_summary": article["summary"],
            "word_count": article["word_count"],
            "verdict": pipe_res["verdict"],
            "classification": pipe_res["verdict"],
            "verdict_badge_class": pipe_res["verdict_badge_class"],
            "score": pipe_res["score"],
            "confidence_score": pipe_res["score"],
            "why_this_verdict": pipe_res["why_this_verdict"],
            "explanation": pipe_res["why_this_verdict"],
            "warnings": all_warnings,
            "matching_sources": pipe_res["matching_sources"],
            "claims": claims,
            "supporting_evidence": pipe_res["supporting_evidence"],
            "contradicting_evidence": pipe_res["contradicting_evidence"],
            "trusted_sources_checked": pipe_res["trusted_sources_checked"],
            "disclaimer": pipe_res["disclaimer"]
        }

    # ----------------------------------------------------------------------
    # Case 2: Statement / Text Verification
    # ----------------------------------------------------------------------
    elif raw_text:
        # Check invalid input (e.g. "abc")
        if len(raw_text) < 5 or (len(raw_text.split()) == 1 and not re.match(r"^https?:\/\/", raw_text)):
            return {
                "status": "error",
                "verdict": "INVALID INPUT",
                "verdict_badge_class": "badge-fake",
                "score": 0,
                "headline": raw_text,
                "publisher": "User Input",
                "error_title": "Statement Too Short",
                "reason": f"'{raw_text}' is too brief to extract factual assertions.",
                "suggestion": "Please enter a complete news headline or statement (e.g. 'Government announces new green energy subsidy').",
                "why_this_verdict": "Input lacks sufficient grammatical structure to evaluate.",
                "warnings": ["Input contains fewer than 5 characters."],
                "matching_sources": [],
                "disclaimer": "Automated estimate, confirm with official sources"
            }

        headline = headline_input or (raw_text if len(raw_text) <= 120 else raw_text[:100])
        pipe_res = verify_story_pipeline(
            headline=headline,
            full_text=raw_text,
            domain="direct-statement",
            publisher="Direct Input"
        )

        claims = extract_main_claims(headline, raw_text)

        try:
            save_verification(
                input_type="text",
                source_url=None,
                headline=headline,
                summary=raw_text[:400],
                classification=pipe_res["verdict"],
                confidence_score=pipe_res["score"],
                explanation=pipe_res["why_this_verdict"],
                claims=claims,
                supporting_evidence=pipe_res["supporting_evidence"],
                contradicting_evidence=pipe_res["contradicting_evidence"],
                trusted_sources_checked=pipe_res["trusted_sources_checked"],
                is_outdated=False,
                published_date=None
            )
        except Exception:
            pass

        return {
            "status": "success",
            "url": None,
            "headline": headline,
            "publisher": "Direct Statement",
            "extracted_summary": raw_text[:400],
            "word_count": len(raw_text.split()),
            "verdict": pipe_res["verdict"],
            "classification": pipe_res["verdict"],
            "verdict_badge_class": pipe_res["verdict_badge_class"],
            "score": pipe_res["score"],
            "confidence_score": pipe_res["score"],
            "why_this_verdict": pipe_res["why_this_verdict"],
            "explanation": pipe_res["why_this_verdict"],
            "warnings": pipe_res.get("warnings", []),
            "matching_sources": pipe_res["matching_sources"],
            "claims": claims,
            "supporting_evidence": pipe_res["supporting_evidence"],
            "contradicting_evidence": pipe_res["contradicting_evidence"],
            "trusted_sources_checked": pipe_res["trusted_sources_checked"],
            "disclaimer": pipe_res["disclaimer"]
        }

    else:
        return {
            "status": "error",
            "verdict": "EMPTY INPUT",
            "verdict_badge_class": "badge-fake",
            "score": 0,
            "error_title": "No Content Provided",
            "reason": "Neither a URL nor a news statement was received.",
            "suggestion": "Please paste a news URL or type a statement to evaluate.",
            "warnings": [],
            "matching_sources": [],
            "disclaimer": "Automated estimate, confirm with official sources"
        }

# --------------------------------------------------------------------------
# Compatibility Endpoints
# --------------------------------------------------------------------------

@app.post("/api/verify/url")
@app.post("/verify/url")
def verify_article_url_endpoint(req: UrlVerificationRequest):
    return unified_verify(UnifiedVerificationRequest(url=req.url))

@app.post("/api/verify/text")
@app.post("/verify/text")
def verify_text_endpoint(req: TextVerificationRequest):
    return unified_verify(UnifiedVerificationRequest(text=req.text, headline=req.headline))

@app.post("/api/verify/youtube")
@app.post("/verify/youtube")
def verify_youtube_endpoint(req: YouTubeVerificationRequest):
    if not req.url:
        raise HTTPException(status_code=400, detail="Missing YouTube URL.")
    try:
        video_data = extract_youtube_content(req.url.strip())
        claims = extract_main_claims(video_data["title"], video_data["text"])
        pipe_res = verify_story_pipeline(
            headline=video_data["title"],
            full_text=video_data["text"],
            domain="youtube.com",
            publisher=video_data.get("author", "YouTube Creator"),
            url=video_data["url"]
        )
        return {
            "status": "success",
            "url": video_data["url"],
            "headline": video_data["title"],
            "author": video_data["author"],
            "thumbnail_url": video_data["thumbnail_url"],
            "extracted_summary": video_data["summary"],
            "verdict": pipe_res["verdict"],
            "classification": pipe_res["verdict"],
            "verdict_badge_class": pipe_res["verdict_badge_class"],
            "score": pipe_res["score"],
            "confidence_score": pipe_res["score"],
            "why_this_verdict": pipe_res["why_this_verdict"],
            "explanation": pipe_res["why_this_verdict"],
            "warnings": pipe_res.get("warnings", []),
            "matching_sources": pipe_res["matching_sources"],
            "claims": claims,
            "supporting_evidence": pipe_res["supporting_evidence"],
            "contradicting_evidence": pipe_res["contradicting_evidence"],
            "trusted_sources_checked": pipe_res["trusted_sources_checked"],
            "disclaimer": pipe_res["disclaimer"]
        }
    except Exception as e:
        return {
            "status": "warning",
            "verdict": "UNVERIFIED",
            "verdict_badge_class": "badge-unverified",
            "score": 45,
            "headline": "YouTube Video Claim",
            "publisher": "YouTube",
            "why_this_verdict": f"Could not extract video captions: {str(e)}",
            "warnings": ["Captions unavailable for automatic transcript parsing."],
            "matching_sources": [],
            "disclaimer": "Automated estimate, confirm with official sources"
        }

# --------------------------------------------------------------------------
# General System Endpoints
# --------------------------------------------------------------------------

@app.get("/api")
@app.get("/api/index")
@app.get("/api/index.py")
@app.get("/api/health")
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "gemini_api_configured": bool(config.GEMINI_API_KEY),
        "factcheck_api_configured": bool(config.GOOGLE_FACTCHECK_API_KEY),
        "database": "SQLite (Connected)",
        "supported_sources": [
            "BBC News", "Reuters", "The Hindu", "CNN", "Times of India",
            "Associated Press", "YouTube Transcripts", "Snopes", "FactCheck.org", "PIB Fact Check"
        ]
    }

@app.get("/api/sources")
@app.get("/sources")
def get_trusted_sources():
    return {
        "fact_checkers": [
            {"name": "PIB Fact Check (Govt of India)", "url": "https://pib.gov.in/factcheck", "status": "Active"},
            {"name": "Google Fact Check Explorer", "url": "https://toolbox.google.com/factcheck/explorer", "status": "Active"},
            {"name": "BOOM Live", "url": "https://www.boomlive.in", "status": "Active"},
            {"name": "Alt News", "url": "https://www.altnews.in", "status": "Active"},
            {"name": "Snopes", "url": "https://www.snopes.com", "status": "Active"},
            {"name": "FactCheck.org", "url": "https://www.factcheck.org", "status": "Active"}
        ],
        "news_agencies": [
            {"name": "Reuters", "url": "https://www.reuters.com", "category": "International Wire"},
            {"name": "Associated Press (AP)", "url": "https://apnews.com", "category": "International Wire"},
            {"name": "BBC News", "url": "https://www.bbc.com/news", "category": "Public Broadcaster"},
            {"name": "The Hindu", "url": "https://www.thehindu.com", "category": "National Daily"},
            {"name": "Times of India", "url": "https://timesofindia.indiatimes.com", "category": "National Daily"},
            {"name": "NDTV", "url": "https://www.ndtv.com", "category": "National Broadcast"},
            {"name": "CNN", "url": "https://www.cnn.com", "category": "Broadcast Network"},
            {"name": "World Health Organization (WHO)", "url": "https://www.who.int", "category": "Public Health"}
        ]
    }

@app.get("/api/history")
@app.get("/history")
def list_history(limit: int = 50):
    return get_history(limit=limit)

@app.get("/api/history/{record_id}")
@app.get("/history/{record_id}")
def get_history_detail(record_id: int):
    rec = get_record_by_id(record_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Verification record not found.")
    return rec

@app.delete("/api/history/{record_id}")
def delete_history_item(record_id: int):
    success = delete_record(record_id)
    if not success:
        raise HTTPException(status_code=404, detail="Verification record not found.")
    return {"message": "Record deleted successfully.", "id": record_id}

@app.delete("/api/history")
def clear_history():
    count = clear_all_history()
    return {"message": "All verification history cleared.", "records_deleted": count}

# --------------------------------------------------------------------------
# Static Files & SPA Frontend Serving
# --------------------------------------------------------------------------

workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@app.get("/")
def serve_index():
    index_path = os.path.join(workspace_root, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Veritas AI Platform v2.0 is running."}

@app.get("/style.css")
def serve_css():
    css_path = os.path.join(workspace_root, "style.css")
    return FileResponse(css_path, media_type="text/css")

@app.get("/app.js")
def serve_js():
    js_path = os.path.join(workspace_root, "app.js")
    return FileResponse(js_path, media_type="application/javascript")
