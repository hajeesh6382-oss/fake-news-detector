import re
import json
import logging
from typing import List, Dict, Any, Optional
from backend.config import config
from backend.models.evidence import ClaimItem

logger = logging.getLogger(__name__)

def extract_claims_with_gemini(headline: str, text: str) -> Optional[List[ClaimItem]]:
    """
    Calls Google Gemini API to extract factual claims with structured schema.
    """
    if not config.GEMINI_API_KEY:
        return None

    prompt = f"""You are an expert news analyst and factual claim extractor.
Analyze the following news headline and content.
Identify the central verifiable factual claims, supporting statements, numerical assertions, and quotations.

Headline: {headline}

Article Text:
{text[:3500]}

Respond ONLY with a valid JSON object matching this schema:
{{
  "headline": "{headline}",
  "claims": [
    {{
      "id": 1,
      "claim": "Direct factual claim",
      "importance": "high",
      "type": "factual",
      "verification_status": "pending"
    }}
  ]
}}
Do NOT output markdown code blocks (no ```json or ```). Output pure JSON only."""

    try:
        # Try google.genai first
        try:
            from google import genai
            client = genai.Client(api_key=config.GEMINI_API_KEY)
            response = client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=prompt
            )
            raw_text = response.text
        except Exception:
            # Fallback to google.generativeai
            import google.generativeai as legacy_genai
            legacy_genai.configure(api_key=config.GEMINI_API_KEY)
            model = legacy_genai.GenerativeModel(config.GEMINI_MODEL)
            response = model.generate_content(prompt)
            raw_text = response.text

        clean_json = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.I)
        clean_json = re.sub(r"\s*```$", "", clean_json.strip())
        parsed = json.loads(clean_json)

        claims_list: List[ClaimItem] = []
        if isinstance(parsed, dict) and "claims" in parsed:
            for idx, c in enumerate(parsed["claims"], start=1):
                claims_list.append(ClaimItem(
                    id=idx,
                    claim=c.get("claim", ""),
                    importance=c.get("importance", "high") if c.get("importance") in ("high", "medium", "low") else "high",
                    verification_status="pending",
                    type=c.get("type", "factual")
                ))
            if claims_list:
                return claims_list
    except Exception as e:
        logger.warning(f"Gemini claim extraction failed: {e}. Falling back to NLP heuristic extractor.")

    return None

def extract_claims_heuristic(headline: str, text: str) -> List[ClaimItem]:
    """
    Robust rule-based heuristic NLP claim extractor that extracts:
    - Primary headline claim
    - Factual statements with action verbs and statistical figures
    - Direct quotations
    """
    claims: List[ClaimItem] = []
    claim_id = 1

    # 1. Headline Claim
    if headline and len(headline.strip()) > 10:
        claims.append(ClaimItem(
            id=claim_id,
            claim=headline.strip(),
            importance="high",
            type="factual",
            verification_status="pending"
        ))
        claim_id += 1

    # 2. Quotation Claims
    quotes = re.findall(r'"([^"]{20,160})"', text)
    for q in quotes[:2]:
        claims.append(ClaimItem(
            id=claim_id,
            claim=f'Stated: "{q.strip()}"',
            importance="medium",
            type="quote",
            verification_status="pending"
        ))
        claim_id += 1

    # 3. Sentences with statistical / factual action assertions
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 30]
    factual_verbs = [
        "announced", "confirmed", "reported", "launched", "banned", "killed", "arrested",
        "approved", "discovered", "signed", "introduced", "increased", "decreased", "decided"
    ]

    for sent in sentences:
        if claim_id > 5:
            break
        # Skip if already resembles the headline
        if headline and (sent in headline or headline in sent):
            continue
        # Check if sentence contains verifiable indicators
        has_verb = any(re.search(rf"\b{v}\b", sent, re.I) for v in factual_verbs)
        has_num = bool(re.search(r"\b\d+(?:[.,]\d+)?%?\b", sent))

        if has_verb or has_num:
            claims.append(ClaimItem(
                id=claim_id,
                claim=sent[:200].strip(),
                importance="high" if has_num else "medium",
                type="statistic" if has_num else "factual",
                verification_status="pending"
            ))
            claim_id += 1

    # Fallback if no specific sentences matched
    if len(claims) <= 1 and sentences:
        for sent in sentences[:2]:
            if claim_id > 4:
                break
            if headline and headline in sent:
                continue
            claims.append(ClaimItem(
                id=claim_id,
                claim=sent[:200].strip(),
                importance="medium",
                type="factual",
                verification_status="pending"
            ))
            claim_id += 1

    return claims

def extract_article_claims(headline: str, text: str) -> List[ClaimItem]:
    """Unified entrypoint: tries Gemini first, falls back to heuristic extractor."""
    ai_claims = extract_claims_with_gemini(headline, text)
    if ai_claims:
        return ai_claims
    return extract_claims_heuristic(headline, text)

