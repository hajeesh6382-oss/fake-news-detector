import re
import math
from collections import Counter
from typing import List, Dict, Any, Set, Tuple, Optional

# Common English stop words
STOP_WORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "arent", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "cant", "cannot", "could", "couldnt", "did", "didnt", "do", "does", "doesnt",
    "doing", "dont", "down", "during", "each", "few", "for", "from", "further", "had", "hadnt",
    "has", "hasnt", "have", "havent", "having", "he", "hed", "hell", "hes", "her", "here",
    "heres", "hers", "herself", "him", "himself", "his", "how", "hows", "i", "id", "ill", "im",
    "ive", "if", "in", "into", "is", "isnt", "it", "its", "itself", "lets", "me", "more", "most",
    "mustnt", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
    "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shant", "she", "shed",
    "shell", "shes", "should", "shouldnt", "so", "some", "such", "than", "that", "thats", "the",
    "their", "theirs", "them", "themselves", "then", "there", "theres", "these", "they", "theyd",
    "theyll", "theyre", "theyve", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasnt", "we", "wed", "well", "were", "weve", "werent", "what", "whats", "when",
    "whens", "where", "wheres", "which", "while", "who", "whos", "whom", "why", "whys", "with",
    "wont", "would", "wouldnt", "you", "youd", "youll", "youre", "youve", "your", "yours",
    "yourself", "yourselves"
}

def tokenize(text: str) -> List[str]:
    """Tokenizes alphanumeric words longer than 2 chars excluding stop words."""
    if not text:
        return []
    words = re.findall(r"\b[a-zA-Z0-9]{3,}\b", text.lower())
    return [w for w in words if w not in STOP_WORDS]

def compute_tfidf_similarity(text1: str, text2: str) -> float:
    """Computes TF-IDF cosine similarity percentage (0-100) between two statements."""
    if not text1 or not text2:
        return 0.0

    tokens1 = tokenize(text1)
    tokens2 = tokenize(text2)
    if not tokens1 or not tokens2:
        return 0.0

    all_terms = set(tokens1).union(tokens2)
    c1, c2 = Counter(tokens1), Counter(tokens2)
    len1, len2 = len(tokens1), len(tokens2)

    vec1, vec2 = {}, {}
    for term in all_terms:
        df = (1 if term in c1 else 0) + (1 if term in c2 else 0)
        idf = math.log((1 + 2) / (1 + df)) + 1.0
        vec1[term] = (c1[term] / len1) * idf
        vec2[term] = (c2[term] / len2) * idf

    dot = sum(vec1[t] * vec2[t] for t in all_terms)
    norm1 = math.sqrt(sum(v * v for v in vec1.values()))
    norm2 = math.sqrt(sum(v * v for v in vec2.values()))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return round(float(dot / (norm1 * norm2)) * 100, 1)

def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Heuristic entity extractor identifying organizations, people/titles,
    locations, numerical facts, and dates from news text.
    """
    entities: Dict[str, List[str]] = {
        "organizations": [],
        "people": [],
        "locations": [],
        "numbers": [],
        "quotes": []
    }
    if not text:
        return entities

    # Common Org keywords
    org_pattern = r"\b([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*(?:\s+(?:Ministry|Department|Police|Court|Commission|Agency|Government|Party|Bank|Hospital|University|Force|Authority|Parliament|Congress|Senate|Council)))\b"
    for m in re.finditer(org_pattern, text):
        org = m.group(1).strip()
        if org not in entities["organizations"] and len(org) > 3:
            entities["organizations"].append(org)

    # Common Title / People patterns
    people_pattern = r"\b((?:Prime Minister|President|Chief Minister|Governor|Director|General|Minister|Secretary|Judge|Dr\.|Spokesperson|Officer)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b"
    for m in re.finditer(people_pattern, text):
        person = m.group(1).strip()
        if person not in entities["people"]:
            entities["people"].append(person)

    # Locations
    loc_pattern = r"\b(?:in|at|from|near)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b"
    for m in re.finditer(loc_pattern, text):
        loc = m.group(1).strip()
        if loc not in entities["locations"] and loc not in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"):
            entities["locations"].append(loc)

    # Numerical statistics
    num_pattern = r"\b(\d+(?:,\d+)*(?:\.\d+)?(?:\s*(?:percent|%|crore|lakh|billion|million|thousand|rupees|dollars|₹|\$|dead|injured|cases|tonnes|km|miles))?)\b"
    for m in re.finditer(num_pattern, text, re.I):
        val = m.group(1).strip()
        if len(val) > 1 and val not in entities["numbers"]:
            entities["numbers"].append(val)

    # Quotations
    quote_pattern = r'"([^"]{15,140})"'
    for m in re.finditer(quote_pattern, text):
        entities["quotes"].append(m.group(1).strip())

    return entities

def is_syndicated_reprint(text1: str, text2: str) -> Tuple[bool, Optional[str]]:
    """
    Detects if two news articles are verbatim wire reprints (e.g. from Reuters, AP, ANI, PTI).
    Articles sharing >= 85% exact paragraph matches are syndicated copies, not independent confirmations.
    """
    if not text1 or not text2:
        return False, None

    # Check wire credits
    wire_agencies = ["Reuters", "Associated Press", "AP", "ANI", "Press Trust of India", "PTI", "AFP", "Bloomberg"]
    t1_lower = text1.lower()
    t2_lower = text2.lower()
    for wire in wire_agencies:
        w_low = wire.lower()
        if f"({w_low})" in t1_lower and f"({w_low})" in t2_lower:
            return True, wire
        if f"reported by {w_low}" in t1_lower and f"reported by {w_low}" in t2_lower:
            return True, wire

    sim = compute_tfidf_similarity(text1, text2)
    if sim >= 88.0:
        return True, "Syndicated Wire Text"

    return False, None
