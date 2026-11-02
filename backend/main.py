import os
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.config import config
from backend.database.db import init_db
from backend.api.verification import router as verification_router, run_verification_pipeline
from backend.api.news_search import router as search_router
from backend.api.history import router as history_router
from backend.extractors.youtube_extractor import extract_youtube_content
from backend.models.verdict import VerdictResult

# Initialize SQLite database
init_db()

app = FastAPI(
    title="Veritas AI Enterprise v2.0",
    description="Advanced AI-Powered Cross-Platform News Verification Platform",
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

# Include Modular Routers
app.include_router(verification_router)
app.include_router(search_router)
app.include_router(history_router)

# Root-level aliases for Vercel Serverless Function compatibility
@app.post("/verify")
@app.post("/verify/url")
@app.post("/api/verify.py")
@app.post("/api/index.py")
async def verify_alias_endpoint(req: Dict[str, Any]):
    url = req.get("url")
    text = req.get("text")
    headline = req.get("headline")
    if url:
        return await run_verification_pipeline(url=url)
    return await run_verification_pipeline(text=text, headline_input=headline)

# --------------------------------------------------------------------------
# YouTube Video Verification Endpoint
# --------------------------------------------------------------------------

class YouTubeVerificationRequest(BaseModel):
    url: str

@app.post("/api/verify/youtube")
@app.post("/verify/youtube")
async def verify_youtube_endpoint(req: YouTubeVerificationRequest):
    """
    POST /api/verify/youtube
    Extracts transcript / metadata from YouTube and runs cross-platform verification.
    """
    if not req.url:
        raise HTTPException(status_code=400, detail="YouTube URL is required")

    yt_data = extract_youtube_content(req.url)
    claim_text = yt_data.get("transcript") or yt_data.get("title", "")
    headline = yt_data.get("title", "YouTube Video")

    # Run verification pipeline on spoken transcript / title
    verdict_res = await run_verification_pipeline(
        text=claim_text[:2000],
        headline_input=headline
    )

    res_dict = verdict_res.dict()
    res_dict.update({
        "input_type": "youtube",
        "video_id": yt_data.get("video_id"),
        "author": yt_data.get("author", "YouTube Creator"),
        "thumbnail_url": yt_data.get("thumbnail_url"),
        "has_transcript": yt_data.get("has_transcript", False)
    })
    return res_dict

# --------------------------------------------------------------------------
# General System Endpoints
# --------------------------------------------------------------------------

@app.get("/api")
@app.get("/api/index")
@app.get("/api/index.py")
@app.get("/api/health")
@app.get("/health")
def health_check():
    """GET /api/health - Returns API health and capability status."""
    return {
        "status": "healthy",
        "app": "Veritas AI Enterprise v2.0",
        "version": "2.0.0",
        "gemini_api_configured": bool(config.GEMINI_API_KEY),
        "news_api_configured": bool(config.NEWS_API_KEY),
        "factcheck_api_configured": bool(config.GOOGLE_FACTCHECK_API_KEY),
        "database": "SQLite (Connected)",
        "supported_sources": {
            "international": list(config.INTERNATIONAL_SOURCES.values()),
            "indian": list(config.INDIAN_SOURCES.values()),
            "fact_checkers": list(config.FACT_CHECK_SOURCES.values()),
            "data_engines": ["GDELT Project 2.0", "Google News RSS", "YouTube Transcripts"]
        }
    }

@app.get("/api/sources")
@app.get("/sources")
def get_trusted_sources():
    """GET /api/sources - Lists accredited news publishers."""
    return {
        "international_sources": [
            {"domain": k, "name": v, "status": "Active Wire Index"}
            for k, v in config.INTERNATIONAL_SOURCES.items()
        ],
        "indian_sources": [
            {"domain": k, "name": v, "status": "Active Wire Index"}
            for k, v in config.INDIAN_SOURCES.items()
        ],
        "fact_checkers": [
            {"domain": k, "name": v, "status": "Verified Debunk Register"}
            for k, v in config.FACT_CHECK_SOURCES.items()
        ]
    }

# --------------------------------------------------------------------------
# Static Web Frontend Delivery
# --------------------------------------------------------------------------

current_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.dirname(current_dir)

@app.get("/")
def serve_index():
    index_path = os.path.join(workspace_root, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"message": "Veritas AI Enterprise API v2.0"}

@app.get("/style.css")
def serve_css():
    css_path = os.path.join(workspace_root, "style.css")
    if os.path.exists(css_path):
        return FileResponse(css_path, media_type="text/css")
    raise HTTPException(status_code=404, detail="CSS file not found")

@app.get("/app.js")
def serve_js():
    js_path = os.path.join(workspace_root, "app.js")
    if os.path.exists(js_path):
        return FileResponse(js_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="JS file not found")
