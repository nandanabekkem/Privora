
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from ..core.authentication import (
    authorize_user_path,
    canonical_user_id,
    get_current_user,
    validate_numeric_user_path,
)
from ..core.firestore_store import get_document, list_by_field


router = APIRouter(
    prefix="/dormant",
    tags=["Dormant Account Detection"],
)


def get_accounts(user_id: int) -> list[dict]:
    accounts = list_by_field("accounts", "user_id", user_id)
    accounts.extend(
        list_by_field("accounts", "user_id", str(user_id))
    )

    unique = {account["id"]: account for account in accounts}

    return sorted(
        unique.values(),
        key=lambda account: (
            0 if str(account["id"]).isdigit() else 1,
            int(account["id"]) if str(account["id"]).isdigit()
            else str(account["id"]),
        ),
    )


def get_service(account: dict) -> dict:
    service_id = account.get("service_id")

    service = (
        get_document("services", service_id)
        if service_id is not None
        else None
    )

    return service or {
        "name": account.get("service_name", "Unknown service"),
        "website": account.get("website"),
    }


@router.get("/{user_id}")
def detect_dormant_accounts(
    user_id: str,
    days: int = Query(default=90, ge=1, le=3650),
    claims: dict = Depends(get_current_user),
):
    validate_numeric_user_path(user_id)
    user = authorize_user_path(user_id, claims)
    owned_user_id = canonical_user_id(user)

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    accounts = get_accounts(owned_user_id)
    results = []

    for account in accounts:
        last_activity = account.get("last_activity")
        service = get_service(account)

        if last_activity is None:
            is_dormant = None
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
                reason = f"No activity recorded in at least {days} days"
            else:
                reason = f"Activity recorded within the last {days} days"

        results.append(
            {
                "account_id": (
                    int(account["id"])
                    if str(account["id"]).isdigit()
                    else account["id"]
                ),
                "service": service.get("name", "Unknown service"),
                "website": service.get("website"),
                "status": account.get("status", "UNKNOWN"),
                "last_activity": last_activity,
                "is_dormant": is_dormant,
                "days_threshold": days,
                "reason": reason,
                "needs_review": is_dormant is None,
                "requires_user_review": True,
            }
        )

    dormant_count = sum(
        1 for item in results if item["is_dormant"]
    )

    return {
        "user_id": owned_user_id,
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
