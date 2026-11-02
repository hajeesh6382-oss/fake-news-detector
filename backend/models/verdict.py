from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from backend.models.evidence import ClaimItem, EvidenceSource, PlatformComparisonItem, VerificationSummary

class VerdictResult(BaseModel):
    task_id: Optional[str] = None
    status: str = "success"
    url: Optional[str] = None
    domain: Optional[str] = None
    publisher: Optional[str] = None
    headline: str = ""
    published_date: Optional[str] = None
    author: Optional[str] = None
    extracted_summary: str = ""
    word_count: int = 0
    
    # Primary Verdict: REAL NEWS | FAKE NEWS | INSUFFICIENT EVIDENCE | INVALID INPUT | EXTRACTION FAILED | UNVERIFIED | BLOCKED URL
    verdict: str = "INSUFFICIENT EVIDENCE"
    classification: str = "INSUFFICIENT EVIDENCE"
    verdict_badge_class: str = "badge-unverified"
    confidence_score: int = Field(default=50, ge=0, le=100)
    why_this_verdict: str = ""
    explanation: str = ""

    # Structured Components
    claims: List[ClaimItem] = Field(default_factory=list)
    platform_comparison: List[PlatformComparisonItem] = Field(default_factory=list)
    evidence_sources: List[EvidenceSource] = Field(default_factory=list)
    matching_sources: List[Dict[str, Any]] = Field(default_factory=list)
    supporting_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    contradicting_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    summary: VerificationSummary = Field(default_factory=VerificationSummary)
    
    warnings: List[str] = Field(default_factory=list)
    trusted_sources_checked: List[str] = Field(default_factory=list)
    disclaimer: str = "Automated estimate, confirm with official sources"
    created_at: Optional[str] = None

class VerificationStatusResponse(BaseModel):
    task_id: str
    stage: int = 1
    stage_name: str = "Processing"
    status: str = "in_progress"
    percent: int = 0
    result: Optional[VerdictResult] = None
    error: Optional[str] = None
