
from fastapi import APIRouter, Depends, HTTPException

from ..core.authentication import (
    authorize_user_path,
    canonical_user_id,
    get_current_user,
    validate_numeric_user_path,
)
from ..core.firestore_store import get_document, list_by_field


router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
)


def numeric_id(value):
    return int(value) if str(value).isdigit() else value


@router.get("/{user_id}")
def get_audit_logs(user_id: str, claims: dict = Depends(get_current_user)):
    validate_numeric_user_path(user_id)

    user = authorize_user_path(user_id, claims)
    owned_user_id = canonical_user_id(user)

    logs = list_by_field("audit_logs", "user_id", owned_user_id)
    logs.extend(list_by_field("audit_logs", "user_id", str(owned_user_id)))

    unique = {log["id"]: log for log in logs}
    logs = sorted(
        unique.values(),
        key=lambda log: (
            log.get("created_at"),
            str(log["id"]),
        ),
        reverse=True,
    )

    return {
        "user_id": owned_user_id,
        "count": len(logs),
        "logs": [
            {
                "id": numeric_id(log["id"]),
                "privacy_action_id": (
                    numeric_id(log["privacy_action_id"])
                    if log.get("privacy_action_id") is not None
                    else None
                ),
                "event_type": log.get("event_type"),
                "details": log.get("details"),
                "created_at": log.get("created_at"),
            }
            for log in logs
        ],
    }
