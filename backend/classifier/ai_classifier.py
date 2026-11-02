import json
from typing import Dict, Any, List
from backend.config import config
from backend.nlp.sentiment_analyzer import analyze_linguistic_signals
from backend.nlp.claim_extractor import check_headline_body_alignment

# Setup Gemini AI if key is present
gemini_model = None
if config.GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=config.GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
    except Exception as e:
        print(f"Warning: Could not initialize Gemini model: {e}")

def classify_with_gemini(
    headline: str,
    text: str,
    claims: List[Dict[str, Any]],
    factcheck_data: Dict[str, Any],
    linguistic_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Uses Google Gemini LLM to synthesize evidence, evaluate claims, and produce a balanced classification.
    """
    prompt = f"""
You are an expert, impartial Fact-Checking and News Verification AI.
Analyze the following news content and external evidence:

HEADLINE: {headline}
ARTICLE EXCERPT: {text[:1500]}
EXTRACTED CLAIMS: {json.dumps([c.get('claim_text') for c in claims])}
SUPPORTING EVIDENCE FOUND: {json.dumps(factcheck_data.get('supporting_evidence', [])[:4])}
CONTRADICTING EVIDENCE / FACT-CHECKS FOUND: {json.dumps(factcheck_data.get('contradicting_evidence', [])[:4])}
LINGUISTIC CLICKBAIT SIGNALS: {linguistic_data.get('sensationalism_score')}% sensationalism
IS OUTDATED SIGNAL: {factcheck_data.get('is_outdated')} ({factcheck_data.get('outdated_notes')})

CRITICAL GUIDELINES:
1. Classification MUST be strictly one of:
   - "REAL NEWS"
   - "POTENTIALLY FAKE"
   - "MISLEADING"
   - "OUTDATED INFORMATION"
   - "UNVERIFIED"
2. DO NOT classify news as "POTENTIALLY FAKE" simply because no mainstream media report was found. If no definitive corroboration or debunking exists, classify as "UNVERIFIED".
3. If an old historical event is recirculated as breaking news, classify as "OUTDATED INFORMATION".
4. If the headline exaggerates or distorts the underlying facts, classify as "MISLEADING".
5. Provide a confidence score between 30 and 99.

Output MUST be a valid JSON object matching this schema:
{{
  "classification": "REAL NEWS | POTENTIALLY FAKE | MISLEADING | OUTDATED INFORMATION | UNVERIFIED",
  "confidence_score": 85,
  "explanation": "Detailed explanation of why this verdict was reached based on the evidence."
}}
"""
    try:
        response = gemini_model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text)
        valid_classes = {"REAL NEWS", "POTENTIALLY FAKE", "MISLEADING", "OUTDATED INFORMATION", "UNVERIFIED"}
        classification = data.get("classification", "").upper()
        if classification not in valid_classes:
            classification = "UNVERIFIED"

        confidence = int(data.get("confidence_score", 65))
        confidence = max(30, min(99, confidence))
        explanation = data.get("explanation", "AI analyzed claims against available evidence.")

        return {
            "classification": classification,
            "confidence_score": confidence,
            "explanation": explanation,
            "model_used": "Gemini 1.5 Flash (LLM Verification)"
        }
    except Exception as e:
        print(f"Gemini API inference failed, falling back to local NLP engine: {e}")
        return None

def classify_with_local_nlp(
    headline: str,
    text: str,
    claims: List[Dict[str, Any]],
    factcheck_data: Dict[str, Any],
    linguistic_data: Dict[str, Any],
    domain_info: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Robust local heuristic & evidence-based classifier when LLM API key is not configured.
    """
    supporting = factcheck_data.get("supporting_evidence", [])
    contradicting = factcheck_data.get("contradicting_evidence", [])
    is_outdated = factcheck_data.get("is_outdated", False)
    sensationalism = linguistic_data.get("sensationalism_score", 0)
    alignment = check_headline_body_alignment(headline, text)
    domain_trusted = domain_info.get("is_trusted_domain", False) if domain_info else False
    domain_suspicious = domain_info.get("is_suspicious_domain", False) if domain_info else False

    # 1. Outdated detection
    if is_outdated:
        return {
            "classification": "OUTDATED INFORMATION",
            "confidence_score": 88,
            "explanation": factcheck_data.get("outdated_notes") or "Evidence indicates this news reports events from past years that are being recirculated as current news.",
            "model_used": "Veritas NLP & Fact-Check Engine"
        }

    # 2. Definite Fact-Check Debunking (Contradicting evidence from Snopes, Reuters Fact Check, etc.)
    if len(contradicting) > 0:
        top_fc = contradicting[0]
        rating = top_fc.get("rating", "False")
        return {
            "classification": "POTENTIALLY FAKE",
            "confidence_score": 92 if "fact_check" in top_fc.get("type", "") else 82,
            "explanation": f"Claim contradicted by independent fact-checkers ({top_fc.get('source', 'Fact Checker')} rated: '{rating}'). Specific statements conflict with established records.",
            "model_used": "Veritas NLP & Fact-Check Engine"
        }

    # 3. Discrepancy between headline and body (Clickbait / Misleading)
    if not alignment.get("aligned", True):
        return {
            "classification": "MISLEADING",
            "confidence_score": 78,
            "explanation": alignment.get("notes") or "The headline makes assertive claims that are not substantiated by the article content.",
            "model_used": "Veritas NLP & Fact-Check Engine"
        }

    # 4. Verified news reports found from reputable agencies or verified domain
    if len(supporting) >= 2 or (domain_trusted and sensationalism < 25):
        sources = list(set(s.get("source", "Mainstream Media") for s in supporting[:3]))
        src_text = ", ".join(sources) if sources else (domain_info.get("domain") if domain_info else "Official Sources")
        return {
            "classification": "REAL NEWS",
            "confidence_score": 85 if len(supporting) >= 2 else 75,
            "explanation": f"Corroborating reports identified from established journalistic sources ({src_text}). Content maintains standard journalistic attribution and verifiable facts.",
            "model_used": "Veritas NLP & Fact-Check Engine"
        }

    # 5. Heavy sensationalism / clickbait indicators without verified source
    if sensationalism >= 40 or domain_suspicious:
        clickbaits = linguistic_data.get("detected_clickbait", [])
        cb_text = f" ({', '.join(clickbaits[:4])})" if clickbaits else ""
        return {
            "classification": "POTENTIALLY FAKE",
            "confidence_score": 74,
            "explanation": f"High concentration of sensational clickbait patterns{cb_text} and emotional urgency markers without credible institutional attribution.",
            "model_used": "Veritas NLP & Fact-Check Engine"
        }

    # 6. Moderate sensationalism or mild discrepancy
    if sensationalism >= 20:
        return {
            "classification": "MISLEADING",
            "confidence_score": 62,
            "explanation": "Contains exaggerated phrasing or unverified assertions that may distort reader comprehension.",
            "model_used": "Veritas NLP & Fact-Check Engine"
        }

    # 7. Default to UNVERIFIED (Never declare fake simply because missing from trusted news!)
    return {
        "classification": "UNVERIFIED",
        "confidence_score": 50,
        "explanation": "No definitive corroboration or authoritative debunking was found across checked databases. The claim lacks verified third-party documentation at this time.",
        "model_used": "Veritas NLP & Fact-Check Engine"
    }

def verify_and_classify(
    headline: str,
    text: str,
    claims: List[Dict[str, Any]],
    factcheck_data: Dict[str, Any],
    domain_info: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Main entry point for classification.
    Uses Gemini API if enabled, otherwise uses the high-precision local NLP engine.
    """
    linguistic_data = analyze_linguistic_signals(f"{headline} {text}")

    result = None
    if gemini_model:
        result = classify_with_gemini(headline, text, claims, factcheck_data, linguistic_data)

    if not result:
        result = classify_with_local_nlp(headline, text, claims, factcheck_data, linguistic_data, domain_info)

    # Attach linguistic diagnostics
    result["linguistic_diagnostics"] = linguistic_data
    return result
