from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ArticleEntity(BaseModel):
    name: str
    category: str  # "person", "organization", "location", "event", "date", "number"

class ExtractedArticle(BaseModel):
    url: str
    domain: str
    publisher: str
    headline: str
    author: Optional[str] = "Unknown"
    published_date: Optional[str] = None
    text: str
    summary: str
    word_count: int
    entities: List[str] = Field(default_factory=list)
    structured_entities: Dict[str, List[str]] = Field(default_factory=dict)
    is_live_blog: bool = False
    raw_html: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)

class UrlVerificationRequest(BaseModel):
    url: Optional[str] = None

class TextVerificationRequest(BaseModel):
    text: Optional[str] = None
    headline: Optional[str] = None

class UnifiedVerificationRequest(BaseModel):
    url: Optional[str] = None
    text: Optional[str] = None
    headline: Optional[str] = None
