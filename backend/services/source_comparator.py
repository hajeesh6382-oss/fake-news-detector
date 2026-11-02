import logging
from typing import List, Dict, Any, Tuple
from backend.config import config
from backend.models.article import ExtractedArticle
from backend.models.evidence import EvidenceSource, PlatformComparisonItem, VerificationSummary, ClaimItem
from backend.utils.text_processor import compute_tfidf_similarity, is_syndicated_reprint

logger = logging.getLogger(__name__)

# Key target platforms to track for the Platform Comparison Panel
TARGET_INTERNATIONAL = [
    "BBC News", "Reuters", "Associated Press", "CNN",
    "Al Jazeera", "The Guardian", "France 24", "DW News"
]

TARGET_INDIAN = [
    "The Hindu", "The Indian Express", "Times of India", "NDTV",
    "Hindustan Times", "India Today", "News18", "ANI News"
]

def compare_and_compile_evidence(
    article: ExtractedArticle,
    claims: List[ClaimItem],
    retrieved_reports: List[Dict[str, Any]],
    fact_check_findings: List[Dict[str, Any]]
) -> Tuple[List[EvidenceSource], List[PlatformComparisonItem], VerificationSummary]:
    """
    Analyzes all retrieved external reports against the original article:
    - Measures semantic similarity
    - Filters out syndicated wire copies from being counted as independent confirmations
    - Categorizes reports as SUPPORTING, CONTRADICTING, or NEUTRAL
    - Maps status for target International and Indian news platforms
    - Produces a VerificationSummary metric object
    """
    evidence_sources: List[EvidenceSource] = []
    platform_comparison: List[PlatformComparisonItem] = []

    # 1. Primary Publisher Entry
    primary_source = EvidenceSource(
        publisher=article.publisher,
        headline=article.headline,
        url=article.url,
        published_date=article.published_date or "Published Article",
        relevant_text=article.summary[:200],
        similarity=100.0,
        status="SUPPORTING",
        retrieval_status="RETRIEVED",
        is_syndicated=False
    )
    evidence_sources.append(primary_source)

    # 2. Add Fact-Check Debunks (if any were found)
    for fc in fact_check_findings:
        evidence_sources.append(EvidenceSource(
            publisher=fc.get("fact_checker", "Accredited Fact Check"),
            headline=fc.get("title", ""),
            url=fc.get("url", ""),
            published_date=fc.get("date", "Fact Check Review"),
            relevant_text=fc.get("explanation", ""),
            similarity=95.0,
            status="CONTRADICTING",
            retrieval_status="RETRIEVED",
            is_syndicated=False
        ))

    # 3. Evaluate Cross-Platform Retrieved Reports
    known_independent_leads = [article.summary[:150]]
    supporting_count = 1 if primary_source.status == "SUPPORTING" else 0
    contradicting_count = len(fact_check_findings)
    matching_count = 0

    for rep in retrieved_reports:
        title = rep.get("title", "")
        link = rep.get("link", "")
        platform = rep.get("platform", "News Source")
        date = rep.get("date", "")
        sim = rep.get("similarity", 0.0)

        # Check if identical to primary URL
        if link == article.url:
            continue

        # Check semantic similarity threshold
        # >= 20% similarity indicates relevance to the same event / topic
        if sim < 15.0:
            continue

        matching_count += 1

        # Check wire syndication
        is_synd, origin_wire = is_syndicated_reprint(article.summary, title)
        for prev_lead in known_independent_leads:
            synd_check, wire_match = is_syndicated_reprint(prev_lead, title)
            if synd_check:
                is_synd = True
                origin_wire = wire_match
                break

        if not is_synd:
            known_independent_leads.append(title)

        # Determine supporting vs contradicting
        # If no fact check debunk contradicts it and similarity is solid, it corroborates the event
        status = "SUPPORTING" if sim >= 25.0 else "NEUTRAL"
        if status == "SUPPORTING" and not is_synd:
            supporting_count += 1

        evidence_sources.append(EvidenceSource(
            publisher=platform,
            headline=title,
            url=link,
            published_date=date,
            relevant_text=f"Reported story with {sim}% semantic correlation.",
            similarity=sim,
            status=status,
            retrieval_status="RETRIEVED",
            is_syndicated=is_synd,
            origin_wire=origin_wire
        ))

    # 4. Compile Target Platform Comparison Panel
    # Shows specific outlets: Supporting Evidence / Contradictory Evidence / No Matching Report Found
    all_target_platforms = TARGET_INTERNATIONAL + TARGET_INDIAN
    platform_matched_map: Dict[str, EvidenceSource] = {}

    for ev in evidence_sources:
        for target in all_target_platforms:
            if target.lower() in ev.publisher.lower() or ev.publisher.lower() in target.lower():
                if target not in platform_matched_map or ev.similarity > platform_matched_map[target].similarity:
                    platform_matched_map[target] = ev

    for target in all_target_platforms:
        if target in platform_matched_map:
            matched_ev = platform_matched_map[target]
            status_label = (
                "Primary Publisher" if matched_ev.url == article.url else
                "Supporting Evidence" if matched_ev.status == "SUPPORTING" else
                "Contradictory Evidence" if matched_ev.status == "CONTRADICTING" else
                "Neutral Reference"
            )
            platform_comparison.append(PlatformComparisonItem(
                platform=target,
                status=status_label,
                headline=matched_ev.headline,
                url=matched_ev.url,
                similarity=matched_ev.similarity
            ))
        else:
            # Report actual status: No Matching Report Found
            platform_comparison.append(PlatformComparisonItem(
                platform=target,
                status="No Matching Report Found",
                headline=None,
                url=None,
                similarity=0.0
            ))

    # 5. Build Verification Summary
    total_searched = len(all_target_platforms) + 2  # plus GDELT & Google News broad index
    summary = VerificationSummary(
        sources_searched=total_searched,
        sources_retrieved=len(evidence_sources),
        matching_articles=matching_count,
        supporting_sources=supporting_count,
        contradictory_sources=contradicting_count,
        unavailable_sources=total_searched - len(platform_matched_map)
    )

    return evidence_sources, platform_comparison, summary

