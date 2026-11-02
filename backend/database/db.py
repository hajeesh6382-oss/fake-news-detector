import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, desc
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.config import config

Base = declarative_base()

class VerificationRecord(Base):
    __tablename__ = "verification_records"

    id = Column(Integer, primary_key=True, index=True)
    input_type = Column(String(50), default="text")  # "url", "youtube", "text"
    source_url = Column(String(1000), nullable=True)
    headline = Column(String(1000), default="")
    summary = Column(Text, default="")
    classification = Column(String(50), default="UNVERIFIED")  # REAL NEWS, POTENTIALLY FAKE, MISLEADING, OUTDATED INFORMATION, UNVERIFIED
    confidence_score = Column(Integer, default=50)
    explanation = Column(Text, default="")
    claims_json = Column(Text, default="[]")
    supporting_evidence_json = Column(Text, default="[]")
    contradicting_evidence_json = Column(Text, default="[]")
    trusted_sources_checked_json = Column(Text, default="[]")
    is_outdated = Column(Boolean, default=False)
    published_date = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "input_type": self.input_type,
            "source_url": self.source_url,
            "headline": self.headline,
            "summary": self.summary,
            "classification": self.classification,
            "confidence_score": self.confidence_score,
            "explanation": self.explanation,
            "claims": json.loads(self.claims_json or "[]"),
            "supporting_evidence": json.loads(self.supporting_evidence_json or "[]"),
            "contradicting_evidence": json.loads(self.contradicting_evidence_json or "[]"),
            "trusted_sources_checked": json.loads(self.trusted_sources_checked_json or "[]"),
            "is_outdated": self.is_outdated,
            "published_date": self.published_date,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_verification(
    input_type: str,
    headline: str,
    summary: str,
    classification: str,
    confidence_score: int,
    explanation: str,
    claims: List[Dict[str, Any]],
    supporting_evidence: List[Dict[str, Any]],
    contradicting_evidence: List[Dict[str, Any]],
    trusted_sources_checked: List[str],
    source_url: Optional[str] = None,
    is_outdated: bool = False,
    published_date: Optional[str] = None
) -> Dict[str, Any]:
    db: Session = SessionLocal()
    try:
        record = VerificationRecord(
            input_type=input_type,
            source_url=source_url,
            headline=headline[:990] if headline else "",
            summary=summary,
            classification=classification,
            confidence_score=confidence_score,
            explanation=explanation,
            claims_json=json.dumps(claims or []),
            supporting_evidence_json=json.dumps(supporting_evidence or []),
            contradicting_evidence_json=json.dumps(contradicting_evidence or []),
            trusted_sources_checked_json=json.dumps(trusted_sources_checked or []),
            is_outdated=is_outdated,
            published_date=published_date,
            created_at=datetime.utcnow()
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record.to_dict()
    finally:
        db.close()

def get_history(limit: int = 50) -> List[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        records = db.query(VerificationRecord).order_by(desc(VerificationRecord.created_at)).limit(limit).all()
        return [r.to_dict() for r in records]
    finally:
        db.close()

def get_record_by_id(record_id: int) -> Optional[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        record = db.query(VerificationRecord).filter(VerificationRecord.id == record_id).first()
        return record.to_dict() if record else None
    finally:
        db.close()

def delete_record(record_id: int) -> bool:
    db: Session = SessionLocal()
    try:
        record = db.query(VerificationRecord).filter(VerificationRecord.id == record_id).first()
        if record:
            db.delete(record)
            db.commit()
            return True
        return False
    finally:
        db.close()

def clear_all_history() -> int:
    db: Session = SessionLocal()
    try:
        count = db.query(VerificationRecord).delete()
        db.commit()
        return count
    finally:
        db.close()
