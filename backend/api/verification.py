import uuid
import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from pydantic import BaseModel

from backend.models.article import UrlVerificationRequest, TextVerificationRequest, UnifiedVerificationRequest, ExtractedArticle
from backend.models.verdict import VerdictResult, VerificationStatusResponse
from backend.services.article_extractor import extract_article_content
from backend.services.claim_extractor import extract_article_claims
from backend.services.news_search_service import search_cross_platform_news
from backend.services.source_comparator import compare_and_compile_evidence
from backend.services.fact_checker import check_debunk_registry, query_google_factcheck_api, evaluate_claims_against_evidence_with_gemini
from backend.services.verdict_generator import generate_verdict
from backend.database.db import save_verification, get_record_by_id
from backend.config import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Verification"])

# In-Memory Real-Time Progress Tracker
TASK_PROGRESS: Dict[str, Dict[str, Any]] = {}

STAGES = [
    (1, "Extracting news article...", 12),
    (2, "Identifying factual claims...", 25),
    (3, "Searching international news platforms...", 40),
    (4, "Searching Indian news platforms...", 55),
    (5, "Collecting independent reports...", 70),
    (6, "Comparing supporting evidence...", 82),
    (7, "Checking contradictory evidence...", 92),
    (8, "Generating final AI verdict...", 100)
]

def update_task_stage(task_id: str, stage_idx: int, extra_data: Dict[str, Any] = None):
    """Updates the live progress state for a running verification task."""
    if task_id in TASK_PROGRESS:
        s_num, s_name, s_pct = STAGES[stage_idx - 1]
        TASK_PROGRESS[task_id].update({
            "stage": s_num,
            "stage_name": s_name,
            "percent": s_pct,
            "status": "in_progress"
        })
        if extra_data:
            TASK_PROGRESS[task_id].update(extra_data)

async def run_verification_pipeline(
    url: Optional[str] = None,
    text: Optional[str] = None,
    headline_input: Optional[str] = None,
    task_id: Optional[str] = None,
    publisher_override: Optional[str] = None,
    domain_override: Optional[str] = None,
    author_override: Optional[str] = None,
    source_url_override: Optional[str] = None,
    is_trusted_override: Optional[bool] = None
) -> VerdictResult:
    """
    Executes the 8-stage verification pipeline with real cross-platform search,
    claim extraction, and evidence comparison.
    """
    task_id = task_id or str(uuid.uuid4())
    TASK_PROGRESS[task_id] = {
        "task_id": task_id,
        "stage": 1,
        "stage_name": "Extracting news article...",
        "percent": 10,
        "status": "in_progress",
        "result": None,
        "error": None
    }

    try:
        # Stage 1: Extracting news article
        update_task_stage(task_id, 1)
        if url:
            article = extract_article_content(url)
        else:
            # Direct text input or YouTube video
            raw_text = (text or "").strip()
            if len(raw_text) < 5 or (len(raw_text.split()) == 1 and not raw_text.startswith("http")):
                raise ValueError(f"'{raw_text}' is too brief to extract factual assertions.")
            headline = headline_input or (raw_text if len(raw_text) <= 120 else raw_text[:100])
            article = ExtractedArticle(
                url=source_url_override or "",
                domain=domain_override or "direct-input",
                publisher=publisher_override or "Direct Statement",
                headline=headline,
                author=author_override or "User",
                published_date=None,
                text=raw_text,
                summary=raw_text[:400],
                word_count=len(raw_text.split()),
                entities=[],
                warnings=[]
            )

        # Stage 2: Identifying factual claims
        update_task_stage(task_id, 2)
        claims = extract_article_claims(article.headline, article.text)

        # Stage 3 & 4: Searching international & Indian news platforms
        update_task_stage(task_id, 3)
        await asyncio.sleep(0.05)
        update_task_stage(task_id, 4)

        retrieved_reports = await search_cross_platform_news(
            headline=article.headline,
            entities=article.entities,
            primary_domain=article.domain,
            primary_url=article.url
        )

        # Stage 5: Collecting independent reports
        update_task_stage(task_id, 5)

        # Stage 6: Comparing supporting evidence
        update_task_stage(task_id, 6)

        # Stage 7: Checking contradictory evidence & Fact-Check Debunks
        update_task_stage(task_id, 7)
        fact_check_findings = check_debunk_registry(f"{article.headline} {article.summary}")
        if not fact_check_findings and config.GOOGLE_FACTCHECK_API_KEY:
            fact_check_findings.extend(query_google_factcheck_api(article.headline))

        evidence_sources, platform_comparison, summary = compare_and_compile_evidence(
            article=article,
            claims=claims,
            retrieved_reports=retrieved_reports,
            fact_check_findings=fact_check_findings
        )

        # Stage 8: Generating final AI verdict (with Gemini if configured)
        update_task_stage(task_id, 8)
        gemini_eval = evaluate_claims_against_evidence_with_gemini(
            article=article,
            claims=claims,
            evidence_sources=evidence_sources
        )

        verdict_res = generate_verdict(
            article=article,
            claims=claims,
            evidence_sources=evidence_sources,
            platform_comparison=platform_comparison,
            summary=summary,
            gemini_eval=gemini_eval,
            task_id=task_id,
            is_trusted_override=is_trusted_override
        )

        # Persist to Database
        try:
            input_type_val = "youtube" if (source_url_override and "youtube" in source_url_override) else ("url" if url else "text")
            save_verification(
                input_type=input_type_val,
                headline=article.headline,
                summary=article.summary,
                classification=verdict_res.verdict,
                confidence_score=verdict_res.confidence_score,
                explanation=verdict_res.why_this_verdict,
                claims=[c.dict() for c in claims],
                supporting_evidence=verdict_res.supporting_evidence,
                contradicting_evidence=verdict_res.contradicting_evidence,
                trusted_sources_checked=verdict_res.trusted_sources_checked,
                is_outdated=False,
                source_url=article.url or None,
                published_date=article.published_date
            )
        except Exception as e:
            logger.warning(f"Could not persist record to database: {e}")

        TASK_PROGRESS[task_id].update({
            "stage": 8,
            "stage_name": "Completed",
            "percent": 100,
            "status": "completed",
            "result": verdict_res
        })

        return verdict_res

    except (ValueError, PermissionError, TimeoutError, ConnectionError) as client_err:
        err_msg = str(client_err)
        logger.warning(f"Verification error for task {task_id}: {err_msg}")
        is_blocked = isinstance(client_err, PermissionError)
        is_timeout = isinstance(client_err, (TimeoutError, ConnectionError))

        res = VerdictResult(
            task_id=task_id,
            status="error" if not is_timeout else "warning",
            url=url,
            domain="Unknown",
            publisher="Remote Target",
            headline=url or text or "Unparseable Input",
            verdict="INVALID INPUT" if isinstance(client_err, ValueError) else ("BLOCKED URL" if is_blocked else "UNVERIFIED"),
            classification="INVALID INPUT" if isinstance(client_err, ValueError) else "UNVERIFIED",
            verdict_badge_class="badge-fake" if not is_timeout else "badge-unverified",
            confidence_score=0 if not is_timeout else 45,
            why_this_verdict=err_msg,
            explanation=err_msg,
            warnings=[err_msg],
            disclaimer="Automated estimate, confirm with official sources"
        )
        TASK_PROGRESS[task_id].update({
            "status": "failed" if not is_timeout else "completed",
            "percent": 100,
            "error": err_msg,
            "result": res
        })
        return res

    except Exception as e:
        err_msg = f"Internal verification engine failure: {str(e)}"
        logger.error(err_msg, exc_info=True)
        res = VerdictResult(
            task_id=task_id,
            status="error",
            url=url,
            domain="Unknown",
            publisher="System Error",
            headline=url or text or "Error",
            verdict="INSUFFICIENT EVIDENCE",
            classification="INSUFFICIENT EVIDENCE",
            verdict_badge_class="badge-unverified",
            confidence_score=35,
            why_this_verdict=err_msg,
            explanation=err_msg,
            warnings=[err_msg],
            disclaimer="Automated estimate, confirm with official sources"
        )
        TASK_PROGRESS[task_id].update({
            "status": "failed",
            "percent": 100,
            "error": err_msg,
            "result": res
        })
        return res

@router.post("/verify/url", response_model=VerdictResult)
@router.post("/verify", response_model=VerdictResult)
async def verify_url_endpoint(req: UnifiedVerificationRequest):
    """
    POST /api/verify/url & POST /api/verify
    Accepts article URL (or statement text), executes cross-platform verification, and returns evidence report.
    """
    if req.url:
        return await run_verification_pipeline(url=req.url)
    elif req.text:
        return await run_verification_pipeline(text=req.text, headline_input=req.headline)
    else:
        raise HTTPException(status_code=400, detail="Either 'url' or 'text' must be provided.")

@router.post("/verify/text", response_model=VerdictResult)
async def verify_text_endpoint(req: TextVerificationRequest):
    """
    POST /api/verify/text
    Verifies directly submitted text statements against news wires & fact-checkers.
    """
    return await run_verification_pipeline(text=req.text, headline_input=req.headline)

@router.get("/verify/status/{task_id}", response_model=VerificationStatusResponse)
async def get_verification_status(task_id: str):
    """
    GET /api/verify/status/{task_id}
    Returns real-time progress state for a running verification task.
    """
    if task_id not in TASK_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification task '{task_id}' not found."
        )

    task = TASK_PROGRESS[task_id]
    return VerificationStatusResponse(
        task_id=task_id,
        stage=task["stage"],
        stage_name=task["stage_name"],
        status=task["status"],
        percent=task["percent"],
        result=task["result"],
        error=task.get("error")
    )

@router.get("/evidence/{verification_id}")
async def get_evidence_detail(verification_id: int):
    """
    GET /api/evidence/{verification_id}
    Retrieves supporting and contradictory evidence for a past verification record.
    """
    rec = get_record_by_id(verification_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Evidence record not found.")

    return {
        "id": rec["id"],
        "headline": rec["headline"],
        "classification": rec["classification"],
        "confidence_score": rec["confidence_score"],
        "explanation": rec["explanation"],
        "claims": rec["claims"],
        "supporting_evidence": rec["supporting_evidence"],
        "contradicting_evidence": rec["contradicting_evidence"],
        "trusted_sources_checked": rec["trusted_sources_checked"],
        "source_url": rec["source_url"],
        "created_at": rec["created_at"]
    }
