from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Account, User


router = APIRouter(
    prefix="/dormant",
    tags=["Dormant Account Detection"],
)


@router.get("/{user_id}")
def detect_dormant_accounts(
    user_id: int,
    days: int = Query(default=90, ge=1, le=3650),
    db: Session = Depends(get_db),
):
    if user_id <= 0:
        raise HTTPException(
            status_code=422,
            detail="User ID must be a positive integer",
        )

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    accounts = (
        db.query(Account)
        .filter(Account.user_id == user_id)
        .order_by(Account.id)
        .all()
    )

    results = []

    for account in accounts:
        last_activity = account.last_activity

        if last_activity is None:
            is_dormant = True
            reason = (
                "No last-activity date is recorded. "
                "Verify the activity before deciding what to do."
            )
        else:
            if last_activity.tzinfo is None:
                last_activity = last_activity.replace(
                    tzinfo=timezone.utc
                )

            is_dormant = last_activity <= cutoff_date

            if is_dormant:
                reason = (
                    f"No activity recorded in at least {days} days"
                )
            else:
                reason = (
                    f"Activity recorded within the last {days} days"
                )

        results.append(
            {
                "account_id": account.id,
                "service": account.service.name,
                "website": account.service.website,
                "status": account.status,
                "last_activity": account.last_activity,
                "is_dormant": is_dormant,
                "days_threshold": days,
                "reason": reason,
                "requires_user_review": True,
            }
        )

    dormant_count = sum(
        1 for item in results if item["is_dormant"]
    )

    return {
        "user_id": user_id,
        "threshold_days": days,
        "account_count": len(results),
        "dormant_count": dormant_count,
        "accounts": results,
        "note": (
            "Results use recorded database data, not live activity "
            "from external services. Missing activity dates are "
            "flagged for review and do not prove inactivity."
        ),
    }
