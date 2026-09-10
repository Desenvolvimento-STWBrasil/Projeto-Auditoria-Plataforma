from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(text("SELECT 1"))
        db_status = "Ok"
    except Exception:
        db_status = "Error"

    return {
        "status": "Ok" if db_status == "Ok" else "degraded",
        "db_status": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
