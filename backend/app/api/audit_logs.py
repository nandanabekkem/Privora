
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import AuditLog, User

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("/{user_id}")
def get_audit_logs(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    logs = (
        db.query(AuditLog)
        .filter(AuditLog.user_id == user_id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .all()
    )

    return {
        "user_id": user_id,
        "count": len(logs),
        "logs": [
            {
                "id": log.id,
                "privacy_action_id": log.privacy_action_id,
                "event_type": log.event_type,
                "details": log.details,
                "created_at": log.created_at,
            }
            for log in logs
        ],
    }
