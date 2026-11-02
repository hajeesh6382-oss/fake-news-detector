import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.config import config
from backend.models.article import ExtractedArticle
from backend.models.evidence import ClaimItem, EvidenceSource, PlatformComparisonItem, VerificationSummary
from backend.models.verdict import VerdictResult

logger = logging.getLogger(__name__)

def generate_verdict(
    article: ExtractedArticle,
    claims: List[ClaimItem],
    evidence_sources: List[EvidenceSource],
    platform_comparison: List[PlatformComparisonItem],
    summary: VerificationSummary,
    gemini_eval: Optional[Dict[str, Any]] = None,
    task_id: Optional[str] = None
) -> VerdictResult:
    """
    Synthesizes all evidence, domain trust metrics, and Gemini evaluations
    into a standardized final verdict: REAL NEWS, FAKE NEWS, or INSUFFICIENT EVIDENCE.
    """
    warnings: List[str] = list(article.warnings)

    # 1. Check for Active Fact-Checker Debunks (Highest Priority Flag)
    debunked_sources = [ev for ev in evidence_sources if ev.status == "CONTRADICTING"]
    if debunked_sources:
        primary_debunk = debunked_sources[0]
        for c in claims:
            c.verification_status = "contradicted"

        why = f"Directly contradicted by official fact-checker ({primary_debunk.publisher}): {primary_debunk.headline}"
        warnings.append(f"Claim flagged by {primary_debunk.publisher} as demonstrably false.")

        return VerdictResult(
            task_id=task_id,
            status="success",
            url=article.url,
            domain=article.domain,
            publisher=article.publisher,
            headline=article.headline,
            published_date=article.published_date,
            author=article.author,
            extracted_summary=article.summary,
            word_count=article.word_count,
            verdict="FAKE NEWS",
            classification="FAKE NEWS",
            verdict_badge_class="badge-fake",
            confidence_score=94,
            why_this_verdict=why,
            explanation=why,
            claims=claims,
            platform_comparison=platform_comparison,
            evidence_sources=evidence_sources,
            matching_sources=[s.dict() for s in evidence_sources],
            supporting_evidence=[s.dict() for s in evidence_sources if s.status == "SUPPORTING"],
            contradicting_evidence=[s.dict() for s in evidence_sources if s.status == "CONTRADICTING"],
            summary=summary,
            warnings=warnings,
            trusted_sources_checked=list(config.ALL_TRUSTED_DOMAINS[:10]),
            created_at=datetime.utcnow().isoformat()
        )

    # 2. Check Domain Authority & Independent Corroboration
    is_trusted_publisher = article.domain in config.ALL_TRUSTED_DOMAINS
    is_suspicious_domain = any(article.domain.endswith(tld) for tld in config.SUSPICIOUS_TLDS)

    # Count independent external corroborating sources (excluding primary publisher and syndicated duplicates)
    independent_corroborating = [
        ev for ev in evidence_sources
        if ev.status == "SUPPORTING" and ev.url != article.url and not ev.is_syndicated
    ]
    corroboration_count = len(independent_corroborating)

    # Check for sensational clickbait markers
    clickbait_words = [
        "shocking", "miracle", "secret cure", "exposed", "urgent alert",
        "share before banned", "100% cure", "free money", "you won't believe"
    ]
    combined_text = f"{article.headline} {article.summary}".lower()
    found_clickbait = [w for w in clickbait_words if w in combined_text]
    if found_clickbait:
        warnings.append(f"Sensationalist clickbait markers detected: {', '.join(found_clickbait)}.")

    # 3. Determine Overall Verdict & Confidence Score
    # Score calculation strictly reflects evidence strength
    confidence_score = 50

    if gemini_eval and gemini_eval.get("verdict") in ("REAL NEWS", "FAKE NEWS", "INSUFFICIENT EVIDENCE"):
        verdict = gemini_eval["verdict"]
        confidence_score = int(gemini_eval.get("confidence_score", 85))
        why = gemini_eval.get("explanation", "")
        # Update claim statuses from Gemini if present
        eval_map = {item.get("id"): item.get("verification_status") for item in gemini_eval.get("evaluated_claims", [])}
        for c in claims:
            if c.id in eval_map and eval_map[c.id]:
                c.verification_status = eval_map[c.id]
    else:
        # Algorithmic Verdict Synthesis
        if is_suspicious_domain or (found_clickbait and corroboration_count == 0):
            verdict = "FAKE NEWS"
            confidence_score = 85
            why = f"Published by unverified anonymous domain ({article.domain}) with sensational clickbait claims and zero independent corroboration."
            for c in claims:
                c.verification_status = "contradicted"

        elif is_trusted_publisher and corroboration_count >= 1:
            verdict = "REAL NEWS"
            confidence_score = 95 if corroboration_count >= 2 else 90
            other_names = ", ".join([s.publisher for s in independent_corroborating[:2]])
            why = f"Corroborated by accredited international/national news agencies ({other_names}) reporting the same event with high semantic consistency."
            for c in claims:
                c.verification_status = "supported"

        elif is_trusted_publisher and corroboration_count == 0:
            # Trusted publisher exclusive report / live coverage
            verdict = "REAL NEWS"
            confidence_score = 88
            why = f"Published directly by recognized news organization ({article.publisher}) adhering to institutional editorial verification standards."
            for c in claims:
                c.verification_status = "supported"

        elif not is_trusted_publisher and corroboration_count >= 2:
            verdict = "REAL NEWS"
            confidence_score = 82
            why = f"Claims reported by this source are independently corroborated across {corroboration_count} accredited news organizations."
            for c in claims:
                c.verification_status = "supported"

        else:
            # No debunks found, but no independent news reports corroborating either
            verdict = "INSUFFICIENT EVIDENCE"
            confidence_score = 45
            why = "No independent news reports were found reporting this story across indexed international or Indian news wires. Confirm with official primary sources."
            warnings.append("Insufficient cross-platform coverage to verify claims as factual.")
            for c in claims:
                c.verification_status = "unverified"

    # Verdict Badge Classes
    if verdict == "REAL NEWS":
        verdict_badge_class = "badge-real"
    elif verdict == "FAKE NEWS":
        verdict_badge_class = "badge-fake"
    else:
        verdict_badge_class = "badge-unverified"

    return VerdictResult(
        task_id=task_id,
        status="success",
        url=article.url,
        domain=article.domain,
        publisher=article.publisher,
        headline=article.headline,
        published_date=article.published_date,
        author=article.author,
        extracted_summary=article.summary,
        word_count=article.word_count,
        verdict=verdict,
        classification=verdict,
        verdict_badge_class=verdict_badge_class,
        confidence_score=confidence_score,
        why_this_verdict=why,
        explanation=why,
        claims=claims,
        platform_comparison=platform_comparison,
        evidence_sources=evidence_sources,
        matching_sources=[s.dict() for s in evidence_sources],
        supporting_evidence=[s.dict() for s in evidence_sources if s.status == "SUPPORTING"],
        contradicting_evidence=[s.dict() for s in evidence_sources if s.status == "CONTRADICTING"],
        summary=summary,
        warnings=warnings,
        trusted_sources_checked=list(config.ALL_TRUSTED_DOMAINS[:10]),
        created_at=datetime.utcnow().isoformat()
    )

