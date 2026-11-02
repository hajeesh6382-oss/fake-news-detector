from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

class ClaimItem(BaseModel):
    id: int
    claim: str
    importance: Literal["high", "medium", "low"] = "high"
    verification_status: Literal["supported", "contradicted", "unverified", "partially_true", "misleading", "pending"] = "pending"
    type: str = "factual"  # "factual", "quote", "statistic", "assertion"
    supporting_evidence: List[str] = Field(default_factory=list)
    contradicting_evidence: List[str] = Field(default_factory=list)

class EvidenceSource(BaseModel):
    publisher: str
    headline: str
    url: str
    published_date: Optional[str] = None
    relevant_text: str = ""
    similarity: float = 0.0
    status: Literal["SUPPORTING", "CONTRADICTING", "NEUTRAL", "UNAVAILABLE"] = "NEUTRAL"
    retrieval_status: Literal["RETRIEVED", "FAILED", "BLOCKED", "NOT_FOUND"] = "RETRIEVED"
    is_syndicated: bool = False
    origin_wire: Optional[str] = None

class PlatformComparisonItem(BaseModel):
    platform: str
    status: str  # "Supporting Evidence", "Contradictory Evidence", "No Matching Report Found", "Primary Publisher"
    headline: Optional[str] = None
    url: Optional[str] = None
    similarity: float = 0.0

class VerificationSummary(BaseModel):
    sources_searched: int = 0
    sources_retrieved: int = 0
    matching_articles: int = 0
    supporting_sources: int = 0
    contradictory_sources: int = 0
    unavailable_sources: int = 0
