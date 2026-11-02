import re
import json
import logging
import urllib.parse
from typing import List, Dict, Any, Optional
import requests

from backend.config import config
from backend.models.article import ExtractedArticle
from backend.models.evidence import ClaimItem, EvidenceSource

logger = logging.getLogger(__name__)

# Official registry of documented viral debunks & hoaxes
KNOWN_DEBUNKED_CLAIMS = [
    {
        "pattern": r"\b(1000\s*(rupee|rs|note)|new\s*rs\s*1000|rbi.*1000\s*note)\b",
        "fact_checker": "PIB Fact Check",
        "title": "PIB Fact Check: RBI has NOT issued or announced any new ₹1,000 currency notes.",
        "url": "https://pib.gov.in/factcheck",
        "rating": "Fake",
        "date": "Official PIB Debunk",
        "explanation": "PIB Fact Check confirmed the viral claim claiming the Reserve Bank of India is re-introducing ₹1,000 currency notes is completely fake. No such decision has been taken."
    },
    {
        "pattern": r"\b(miracle\s*cure|cure\s*cancer\s*in\s*24\s*hours|doctors\s*hate\s*this\s*100%\s*cure)\b",
        "fact_checker": "BOOM Live & Snopes",
        "title": "Fact Check: Unverified viral alternative health remedies falsely advertised as instant cures.",
        "url": "https://www.boomlive.in",
        "rating": "False",
        "date": "Health Warning",
        "explanation": "Accredited medical authorities and fact-checkers report there is no scientifically approved instant 100% cure."
    },
    {
        "pattern": r"\b(5g\s*causes\s*(covid|corona|virus)|5g\s*radiation\s*virus)\b",
        "fact_checker": "Alt News & WHO",
        "title": "Alt News / WHO: Viruses cannot travel on radio waves or mobile networks.",
        "url": "https://www.altnews.in",
        "rating": "Fake",
        "date": "Medical Fact Check",
        "explanation": "World Health Organization and Alt News confirmed radio waves cannot transmit viruses or biological agents."
    },
    {
        "pattern": r"\b(free\s*recharge\s*scheme|pm\s*free\s*laptop\s*yojana|modi\s*free\s*smartphone)\b",
        "fact_checker": "PIB Fact Check",
        "title": "PIB Fact Check: Government has launched NO such free mobile recharge or laptop distribution scheme.",
        "url": "https://pib.gov.in/factcheck",
        "rating": "Fake",
        "date": "Government Advisory",
        "explanation": "Official PIB fact checks alert citizens against fraudulent phishing links offering free government schemes."
    }
]

def check_debunk_registry(text: str) -> List[Dict[str, Any]]:
    """Checks whether the text matches documented viral hoaxes."""
    matched = []
    if not text:
        return matched
    for debunk in KNOWN_DEBUNKED_CLAIMS:
        if re.search(debunk["pattern"], text, re.I):
            matched.append(debunk)
    return matched

def query_google_factcheck_api(query: str) -> List[Dict[str, Any]]:
    """Queries the Google Fact Check Tools API if an API key is configured."""
    if not config.GOOGLE_FACTCHECK_API_KEY or not query:
        return []

    url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
    params = {
        "query": query[:120],
        "key": config.GOOGLE_FACTCHECK_API_KEY,
        "languageCode": "en"
    }

    results = []
    try:
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            for claim in data.get("claims", [])[:3]:
                reviews = claim.get("claimReview", [])
                if reviews:
                    rev = reviews[0]
                    results.append({
                        "fact_checker": rev.get("publisher", {}).get("name", "Fact Checker"),
                        "title": f"Fact Check: {claim.get('text', '')}",
                        "url": rev.get("url", ""),
                        "rating": rev.get("textualRating", "Contradicted"),
                        "date": rev.get("reviewDate", "Fact Check Review"),
                        "explanation": f"Reviewed by {rev.get('publisher', {}).get('name')}: Rated as {rev.get('textualRating', 'Unverified')}."
                    })
    except Exception as e:
        logger.debug(f"Google Fact Check API query error: {e}")

    return results

def evaluate_claims_against_evidence_with_gemini(
    article: ExtractedArticle,
    claims: List[ClaimItem],
    evidence_sources: List[EvidenceSource]
) -> Optional[Dict[str, Any]]:
    """
    Submits claims and gathered external evidence to Gemini for deep fact verification.
    """
    if not config.GEMINI_API_KEY:
        return None

    evidence_summary_text = "\n".join([
        f"- {ev.publisher} ({ev.status}): '{ev.headline}' [Similarity: {ev.similarity}%] {ev.relevant_text}"
        for ev in evidence_sources[:6]
    ])

    prompt = f"""You are a senior OSINT investigator and professional news fact-checker.
Evaluate whether the news story is genuine, fabricated, or unverified based ONLY on the provided evidence.

Article Headline: {article.headline}
Publisher: {article.publisher} ({article.domain})
Article Summary: {article.summary[:800]}

Extracted Claims:
{json.dumps([{'id': c.id, 'claim': c.claim} for c in claims], indent=2)}

Cross-Platform Evidence Retrieved:
{evidence_summary_text}

Rules:
1. Verdict must be one of: "REAL NEWS", "FAKE NEWS", "INSUFFICIENT EVIDENCE".
2. If multiple independent credible news outlets (e.g. BBC, Reuters, The Hindu, AP) report the same event, verdict is "REAL NEWS".
3. If claims match a documented hoax or are contradicted by fact-checkers, verdict is "FAKE NEWS".
4. If no external independent reporting is found and no debunk exists, verdict is "INSUFFICIENT EVIDENCE".
5. Confidence score must be 0-100 reflecting evidence strength.
6. Provide a concise, clear plain-English explanation.

Respond in pure JSON:
{{
  "verdict": "REAL NEWS",
  "confidence_score": 92,
  "explanation": "Explanation here",
  "evaluated_claims": [
    {{
      "id": 1,
      "verification_status": "supported"
    }}
  ]
}}
Do NOT use markdown code blocks."""

    try:
        try:
            from google import genai
            client = genai.Client(api_key=config.GEMINI_API_KEY)
            resp = client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=prompt
            )
            raw = resp.text
        except Exception:
            import google.generativeai as legacy_genai
            legacy_genai.configure(api_key=config.GEMINI_API_KEY)
            model = legacy_genai.GenerativeModel(config.GEMINI_MODEL)
            resp = model.generate_content(prompt)
            raw = resp.text

        clean_json = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.I)
        clean_json = re.sub(r"\s*```$", "", clean_json.strip())
        data = json.loads(clean_json)

        if isinstance(data, dict) and "verdict" in data:
            return data
    except Exception as e:
        logger.warning(f"Gemini fact analysis failed: {e}")

    return None

