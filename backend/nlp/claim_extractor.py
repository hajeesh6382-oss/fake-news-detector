import re
from typing import List, Dict, Any, Tuple

# Verbs and patterns commonly indicating factual claims
CLAIM_MARKER_VERBS = {
    "announced", "stated", "claimed", "reported", "discovered", "confirmed",
    "banned", "approved", "killed", "injured", "passed", "signed", "warned",
    "declared", "found", "proved", "revealed", "arrested", "filed", "decided"
}

STATISTICAL_PATTERN = re.compile(r"\b(\d+[\d,.]*%?|\$\d+|\bmillion\b|\bbillion\b|\bpercent\b)\b", re.I)
QUOTATION_PATTERN = re.compile(r'["“\'].+?["”\']')

def split_into_sentences(text: str) -> List[str]:
    """Splits body text into clean sentences."""
    cleaned = re.sub(r"\s+", " ", text).strip()
    # Basic sentence boundary split
    raw_sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    valid = []
    for s in raw_sentences:
        s_clean = s.strip()
        if len(s_clean) > 20 and len(s_clean.split()) >= 4:
            valid.append(s_clean)
    return valid

def score_sentence_for_claim(sentence: str, headline: str = "") -> float:
    """Scores how likely a sentence represents a verifiable factual claim."""
    score = 0.0
    s_lower = sentence.lower()
    words = set(re.findall(r"\b[a-z]{3,}\b", s_lower))

    # Boost if words match claim verbs
    for verb in CLAIM_MARKER_VERBS:
        if verb in words:
            score += 2.0

    # Boost if contains numbers, percentages, or monetary statistics
    if STATISTICAL_PATTERN.search(sentence):
        score += 2.5

    # Boost if contains quoted attribution
    if QUOTATION_PATTERN.search(sentence):
        score += 1.5

    # Check relation to headline
    if headline:
        h_words = set(re.findall(r"\b[a-z]{4,}\b", headline.lower()))
        overlap = len(words.intersection(h_words))
        score += overlap * 1.2

    # Length balance (prefer standard length claims between 8 and 30 words)
    w_count = len(words)
    if 8 <= w_count <= 35:
        score += 1.5
    elif w_count > 45:
        score -= 1.0

    return score

def extract_main_claims(title: str, text: str, max_claims: int = 4) -> List[Dict[str, Any]]:
    """
    Extracts the key factual claims from article title and body.
    """
    claims = []

    # 1. Headline is always evaluated as Claim #1 if present
    if title and len(title.strip()) > 10:
        claims.append({
            "id": 1,
            "claim_text": title.strip(),
            "source_type": "headline",
            "verifiable": True,
            "confidence_level": "Primary Statement"
        })

    # 2. Extract top claims from body sentences
    sentences = split_into_sentences(text)
    scored_sentences = []

    for s in sentences:
        # Avoid exact duplicate of headline
        if s.lower() == title.lower() or s in title or title in s:
            continue
        sc = score_sentence_for_claim(s, headline=title)
        scored_sentences.append((sc, s))

    # Sort descending by score
    scored_sentences.sort(key=lambda x: x[0], reverse=True)

    seen_prefixes = set()
    cid = len(claims) + 1

    for sc, sent in scored_sentences:
        if len(claims) >= max_claims:
            break
        # Deduplicate very similar sentences
        prefix = sent[:35].lower()
        if prefix in seen_prefixes:
            continue
        seen_prefixes.add(prefix)

        claims.append({
            "id": cid,
            "claim_text": sent,
            "source_type": "article_body",
            "verifiable": True,
            "confidence_level": "Key Claim" if sc > 3.0 else "Secondary Claim"
        })
        cid += 1

    return claims

def check_headline_body_alignment(title: str, text: str) -> Dict[str, Any]:
    """
    Detects headline-to-body discrepancy or clickbait exaggeration.
    """
    if not title or not text:
        return {"aligned": True, "discrepancy_score": 0.0, "notes": "Insufficient text for divergence analysis."}

    title_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", title.lower()))
    body_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", text.lower()))

    # Ignore generic common words
    stop_words = {"this", "that", "with", "from", "have", "been", "were", "what", "when", "where", "about"}
    title_words = title_words - stop_words

    if not title_words:
        return {"aligned": True, "discrepancy_score": 0.0, "notes": "Normal headline alignment."}

    overlap = len(title_words.intersection(body_words))
    ratio = overlap / len(title_words)

    # Check for sensational exaggeration in headline not in body
    sensational_words = {"secret", "exposed", "miracle", "shocking", "urgent", "hoax", "banned"}
    sensational_in_title = title_words.intersection(sensational_words)

    if ratio < 0.35 and len(body_words) > 50:
        return {
            "aligned": False,
            "discrepancy_score": 0.75,
            "notes": "Headline contains strong claims or keywords not adequately substantiated in the article body (possible clickbait exaggeration)."
        }
    elif sensational_in_title and ratio < 0.6:
        return {
            "aligned": False,
            "discrepancy_score": 0.55,
            "notes": f"Sensational words in headline ({', '.join(sensational_in_title)}) are not verified in the article text."
        }
    else:
        return {
            "aligned": True,
            "discrepancy_score": 0.1,
            "notes": "Headline aligns well with the extracted article content."
        }
