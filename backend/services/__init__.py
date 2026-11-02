from .article_extractor import extract_article_content
from .claim_extractor import extract_article_claims
from .news_search_service import search_cross_platform_news
from .source_comparator import compare_and_compile_evidence
from .fact_checker import check_debunk_registry, query_google_factcheck_api, evaluate_claims_against_evidence_with_gemini
from .verdict_generator import generate_verdict

__all__ = [
    "extract_article_content",
    "extract_article_claims",
    "search_cross_platform_news",
    "compare_and_compile_evidence",
    "check_debunk_registry",
    "query_google_factcheck_api",
    "evaluate_claims_against_evidence_with_gemini",
    "generate_verdict"
]
