import os
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl

from backend.config import config
from backend.database.db import (
    init_db,
    save_verification,
    get_history,
    get_record_by_id,
    delete_record,
    clear_all_history
)
from backend.extractors.url_extractor import extract_article_from_url
from backend.extractors.youtube_extractor import extract_youtube_content
from backend.nlp.claim_extractor import extract_main_claims
from backend.fact_checking.factcheck_engine import verify_claims_against_trusted_sources
from backend.classifier.ai_classifier import verify_and_classify

# Initialize database
init_db()

app = FastAPI(
    title="Advanced AI-Powered Fake News Detection System",
    description="Intelligent News & Video Verification Platform with Real-Time Fact-Checking and Linguistic AI.",
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

class UrlVerificationRequest(BaseModel):
    url: str

class YouTubeVerificationRequest(BaseModel):
    url: str

class TextVerificationRequest(BaseModel):
    text: str
    headline: Optional[str] = None

# --------------------------------------------------------------------------
# API Endpoints
# --------------------------------------------------------------------------

@app.get("/api/health")
def health_check():
    """System health and active AI capabilities."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "gemini_api_configured": bool(config.GEMINI_API_KEY),
        "factcheck_api_configured": bool(config.GOOGLE_FACTCHECK_API_KEY),
        "database": "SQLite (Connected)",
        "supported_sources": [
            "BBC News", "Reuters", "The Hindu", "CNN", "Times of India",
            "Associated Press", "YouTube Transcripts", "Snopes", "FactCheck.org"
        ]
    }

@app.get("/api/sources")
def get_trusted_sources():
    """Returns the registry of authoritative news organizations and fact-checkers."""
    return {
        "fact_checkers": [
            {"name": "Google Fact Check Explorer", "url": "https://toolbox.google.com/factcheck/explorer", "status": "Active"},
            {"name": "FactCheck.org", "url": "https://www.factcheck.org", "status": "Active"},
            {"name": "Snopes", "url": "https://www.snopes.com", "status": "Active"},
            {"name": "PolitiFact", "url": "https://www.politifact.com", "status": "Active"},
            {"name": "PIB Fact Check (Govt of India)", "url": "https://pib.gov.in/factcheck", "status": "Active"}
        ],
        "news_agencies": [
            {"name": "Reuters", "url": "https://www.reuters.com", "category": "International Wire"},
            {"name": "Associated Press (AP)", "url": "https://apnews.com", "category": "International Wire"},
            {"name": "BBC News", "url": "https://www.bbc.com/news", "category": "Public Broadcaster"},
            {"name": "The Hindu", "url": "https://www.thehindu.com", "category": "National Daily"},
            {"name": "Times of India", "url": "https://timesofindia.indiatimes.com", "category": "National Daily"},
            {"name": "CNN", "url": "https://www.cnn.com", "category": "Broadcast Network"},
            {"name": "World Health Organization (WHO)", "url": "https://www.who.int", "category": "Public Health"}
        ]
    }

@app.post("/api/verify/url")
def verify_article_url(req: UrlVerificationRequest):
    """
    Extracts news article content from a URL, extracts factual claims,
    searches trusted databases for evidence, and produces an AI classification.
    """
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="Please enter a valid news article URL.")

    # 1. Extract content from URL
    try:
        article = extract_article_from_url(req.url.strip())
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except (TimeoutError, ConnectionError) as ce:
        raise HTTPException(status_code=504, detail=str(ce))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process webpage: {str(e)}")

    # 2. Extract Claims
    claims = extract_main_claims(article["title"], article["text"])

    # 3. Real-Time Fact-Checking
    factcheck_data = verify_claims_against_trusted_sources(
        claims=claims,
        headline=article["title"],
        full_text=article["text"]
    )

    # 4. AI Classification
    classification_res = verify_and_classify(
        headline=article["title"],
        text=article["text"],
        claims=claims,
        factcheck_data=factcheck_data,
        domain_info=article
    )

    # 5. Persist to Database
    record = save_verification(
        input_type="url",
        source_url=article["url"],
        headline=article["title"],
        summary=article["summary"],
        classification=classification_res["classification"],
        confidence_score=classification_res["confidence_score"],
        explanation=classification_res["explanation"],
        claims=claims,
        supporting_evidence=factcheck_data["supporting_evidence"],
        contradicting_evidence=factcheck_data["contradicting_evidence"],
        trusted_sources_checked=factcheck_data["trusted_sources_checked"],
        is_outdated=factcheck_data["is_outdated"],
        published_date=article.get("published_date")
    )

    return {
        "record_id": record["id"],
        "input_type": "url",
        "source_url": article["url"],
        "domain": article["domain"],
        "site_name": article["site_name"],
        "headline": article["title"],
        "published_date": article.get("published_date"),
        "author": article.get("author"),
        "extracted_summary": article["summary"],
        "word_count": article["word_count"],
        "claims": claims,
        "classification": classification_res["classification"],
        "confidence_score": classification_res["confidence_score"],
        "explanation": classification_res["explanation"],
        "model_used": classification_res.get("model_used"),
        "linguistic_diagnostics": classification_res.get("linguistic_diagnostics"),
        "supporting_evidence": factcheck_data["supporting_evidence"],
        "contradicting_evidence": factcheck_data["contradicting_evidence"],
        "trusted_sources_checked": factcheck_data["trusted_sources_checked"],
        "is_outdated": factcheck_data["is_outdated"],
        "outdated_notes": factcheck_data.get("outdated_notes"),
        "created_at": record["created_at"]
    }

@app.post("/api/verify/youtube")
def verify_youtube_video(req: YouTubeVerificationRequest):
    """
    Extracts speech transcripts and metadata from a YouTube video URL,
    extracts spoken claims, and verifies them against trusted sources.
    """
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="Please enter a valid YouTube video URL.")

    # 1. Extract YouTube content & transcript
    try:
        video_data = extract_youtube_content(req.url.strip())
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"YouTube extraction error: {str(e)}")

    # 2. Extract Claims from Transcript
    claims = extract_main_claims(video_data["title"], video_data["text"])

    # 3. Real-Time Fact-Checking
    factcheck_data = verify_claims_against_trusted_sources(
        claims=claims,
        headline=video_data["title"],
        full_text=video_data["text"]
    )

    # 4. AI Classification
    classification_res = verify_and_classify(
        headline=video_data["title"],
        text=video_data["text"],
        claims=claims,
        factcheck_data=factcheck_data,
        domain_info={"domain": "youtube.com", "is_trusted_domain": False, "is_suspicious_domain": False}
    )

    # 5. Persist to Database
    record = save_verification(
        input_type="youtube",
        source_url=video_data["url"],
        headline=video_data["title"],
        summary=video_data["summary"],
        classification=classification_res["classification"],
        confidence_score=classification_res["confidence_score"],
        explanation=classification_res["explanation"],
        claims=claims,
        supporting_evidence=factcheck_data["supporting_evidence"],
        contradicting_evidence=factcheck_data["contradicting_evidence"],
        trusted_sources_checked=factcheck_data["trusted_sources_checked"],
        is_outdated=factcheck_data["is_outdated"],
        published_date=None
    )

    return {
        "record_id": record["id"],
        "input_type": "youtube",
        "source_url": video_data["url"],
        "video_id": video_data["video_id"],
        "headline": video_data["title"],
        "author": video_data["author"],
        "thumbnail_url": video_data["thumbnail_url"],
        "extracted_summary": video_data["summary"],
        "transcript_segments": video_data.get("transcript_segments", []),
        "word_count": video_data["word_count"],
        "claims": claims,
        "classification": classification_res["classification"],
        "confidence_score": classification_res["confidence_score"],
        "explanation": classification_res["explanation"],
        "model_used": classification_res.get("model_used"),
        "linguistic_diagnostics": classification_res.get("linguistic_diagnostics"),
        "supporting_evidence": factcheck_data["supporting_evidence"],
        "contradicting_evidence": factcheck_data["contradicting_evidence"],
        "trusted_sources_checked": factcheck_data["trusted_sources_checked"],
        "is_outdated": factcheck_data["is_outdated"],
        "outdated_notes": factcheck_data.get("outdated_notes"),
        "created_at": record["created_at"]
    }

@app.post("/api/verify/text")
def verify_text_content(req: TextVerificationRequest):
    """
    Verifies raw news statements, headlines, or social media text.
    """
    raw_text = req.text.strip() if req.text else ""
    if not raw_text:
        raise HTTPException(status_code=400, detail="Please enter news headline or text to verify.")

    headline = req.headline.strip() if req.headline else ""
    if not headline:
        # If text is short, it's the headline; if long, use first sentence as headline
        if len(raw_text) <= 120:
            headline = raw_text
        else:
            first_period = raw_text.find(".")
            headline = raw_text[:first_period] if first_period > 10 else raw_text[:100]

    # 1. Extract Claims
    claims = extract_main_claims(headline, raw_text)

    # 2. Real-Time Fact-Checking
    factcheck_data = verify_claims_against_trusted_sources(
        claims=claims,
        headline=headline,
        full_text=raw_text
    )

    # 3. AI Classification
    classification_res = verify_and_classify(
        headline=headline,
        text=raw_text,
        claims=claims,
        factcheck_data=factcheck_data
    )

    # 4. Persist to Database
    record = save_verification(
        input_type="text",
        source_url=None,
        headline=headline,
        summary=raw_text[:400],
        classification=classification_res["classification"],
        confidence_score=classification_res["confidence_score"],
        explanation=classification_res["explanation"],
        claims=claims,
        supporting_evidence=factcheck_data["supporting_evidence"],
        contradicting_evidence=factcheck_data["contradicting_evidence"],
        trusted_sources_checked=factcheck_data["trusted_sources_checked"],
        is_outdated=factcheck_data["is_outdated"],
        published_date=None
    )

    return {
        "record_id": record["id"],
        "input_type": "text",
        "headline": headline,
        "extracted_summary": raw_text[:400],
        "word_count": len(raw_text.split()),
        "claims": claims,
        "classification": classification_res["classification"],
        "confidence_score": classification_res["confidence_score"],
        "explanation": classification_res["explanation"],
        "model_used": classification_res.get("model_used"),
        "linguistic_diagnostics": classification_res.get("linguistic_diagnostics"),
        "supporting_evidence": factcheck_data["supporting_evidence"],
        "contradicting_evidence": factcheck_data["contradicting_evidence"],
        "trusted_sources_checked": factcheck_data["trusted_sources_checked"],
        "is_outdated": factcheck_data["is_outdated"],
        "outdated_notes": factcheck_data.get("outdated_notes"),
        "created_at": record["created_at"]
    }

# --------------------------------------------------------------------------
# History Database Endpoints
# --------------------------------------------------------------------------

@app.get("/api/history")
def list_history(limit: int = 50):
    """Retrieve past verification records stored in SQLite database."""
    return get_history(limit=limit)

@app.get("/api/history/{record_id}")
def get_history_detail(record_id: int):
    """Retrieve full details of an individual verification record."""
    rec = get_record_by_id(record_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Verification record not found.")
    return rec

@app.delete("/api/history/{record_id}")
def delete_history_item(record_id: int):
    """Delete a specific verification record."""
    success = delete_record(record_id)
    if not success:
        raise HTTPException(status_code=404, detail="Verification record not found.")
    return {"message": "Record deleted successfully.", "id": record_id}

@app.delete("/api/history")
def clear_history():
    """Clear all records from verification history."""
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
    return {"message": "Fake News Detector API 2.0 is running."}

@app.get("/style.css")
def serve_css():
    css_path = os.path.join(workspace_root, "style.css")
    return FileResponse(css_path, media_type="text/css")

@app.get("/app.js")
def serve_js():
    js_path = os.path.join(workspace_root, "app.js")
    return FileResponse(js_path, media_type="application/javascript")
