from .factcheck_engine import (
    verify_story_pipeline,
    check_known_debunks,
    search_cross_platform_news,
    compute_tfidf_similarity
)

# Backwards compatibility alias
verify_claims_against_trusted_sources = verify_story_pipeline
