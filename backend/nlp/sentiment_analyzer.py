import re
from typing import Dict, Any

CLICKBAIT_PATTERNS = [
    r"\b(shocking|you won't believe|miracle|secret remedy|exposed|hoax|conspiracy)\b",
    r"\b(100% cure|share before banned|forward this|breaking!!!|free money)\b",
    r"\b(instant cure|leaked document|doctors hate|guaranteed|hidden truth)\b",
    r"\b(wake up people|government won't tell you|act fast before|urgent alert)\b"
]

CREDIBLE_PATTERNS = [
    r"\b(according to|official statement|ministry of|published report|researchers found)\b",
    r"\b(clinical trial|peer-reviewed|supreme court|spokesperson confirmed)\b",
    r"\b(press conference|reuters|associated press|bbc news|the hindu)\b",
    r"\b(world health organization|data released|department of|investigation revealed)\b"
]

def analyze_linguistic_signals(text: str) -> Dict[str, Any]:
    """
    Evaluates clickbait intensity, sensationalism, capitalization, and formal journalistic attribution.
    """
    if not text:
        return {
            "sensationalism_score": 0,
            "credibility_score": 0,
            "is_all_caps": False,
            "has_excessive_punctuation": False,
            "detected_clickbait": [],
            "detected_credible": []
        }

    lower_text = text.lower()

    # 1. Punctuation checks
    has_excessive_punct = "!!" in text or "??" in text or "?!" in text

    # 2. Capitalization check
    letters = [ch for ch in text if ch.isalpha()]
    is_all_caps = False
    if len(letters) >= 15:
        cap_count = sum(1 for ch in letters if ch.isupper())
        is_all_caps = (cap_count / len(letters)) > 0.65

    # 3. Clickbait matches
    detected_clickbait = []
    for pat in CLICKBAIT_PATTERNS:
        matches = re.findall(pat, lower_text)
        detected_clickbait.extend(matches)
    detected_clickbait = list(set(detected_clickbait))

    # 4. Credible attribution matches
    detected_credible = []
    for pat in CREDIBLE_PATTERNS:
        matches = re.findall(pat, lower_text)
        detected_credible.extend(matches)
    detected_credible = list(set(detected_credible))

    # Compute metric scores (0 to 100)
    sensational_points = (len(detected_clickbait) * 18) + (25 if has_excessive_punct else 0) + (30 if is_all_caps else 0)
    sensationalism_score = min(100, sensational_points)

    credible_points = len(detected_credible) * 22
    credibility_score = min(100, credible_points)

    return {
        "sensationalism_score": sensationalism_score,
        "credibility_score": credibility_score,
        "is_all_caps": is_all_caps,
        "has_excessive_punctuation": has_excessive_punct,
        "detected_clickbait": detected_clickbait,
        "detected_credible": detected_credible
    }
