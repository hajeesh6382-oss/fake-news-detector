from typing import List, Optional
from fastapi import APIRouter, HTTPException
from backend.database.db import get_history, get_record_by_id, delete_record, clear_all_history

router = APIRouter(prefix="/api", tags=["History"])

@router.get("/history")
def list_history_records(limit: int = 50):
    """GET /api/history - Retrieves stored verification history."""
    return get_history(limit=limit)

@router.get("/history/{record_id}")
def get_history_item(record_id: int):
    """GET /api/history/{record_id} - Retrieves single verification detail."""
    rec = get_record_by_id(record_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found")
    return rec

@router.delete("/history/{record_id}")
def remove_history_item(record_id: int):
    """DELETE /api/history/{record_id} - Deletes single record."""
    success = delete_record(record_id)
    if not success:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"status": "deleted", "id": record_id}

@router.delete("/history")
def clear_history_records():
    """DELETE /api/history - Clears all history."""
    deleted_count = clear_all_history()
    return {"status": "cleared", "deleted_count": deleted_count}

