from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Account, Policy, User
from app.services.rules_engine import evaluate_account


router = APIRouter(
    prefix="/rules",
    tags=["Privacy Rules Engine"],
)


@router.get("/{user_id}")
def evaluate_user_accounts(
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

    accounts = (
        db.query(Account)
        .filter(Account.user_id == user_id)
        .order_by(Account.id)
        .all()
    )

    policies = (
        db.query(Policy)
        .filter(Policy.user_id == user_id)
        .order_by(Policy.id)
        .all()
    )

    recommendations = []

    for account in accounts:
        recommendation = evaluate_account(
            account,
            days_threshold=days,
            policies=policies,
        )
        recommendations.append(recommendation)

    return {
        "user_id": user_id,
        "days_threshold": days,
        "saved_policy_count": len(policies),
        "account_count": len(accounts),
        "recommendation_count": len(recommendations),
        "recommendations": recommendations,
        "note": (
            "Recommendations use recorded database data and saved policies. "
            "They are suggestions, not proof that an account is unused. "
            "No external accounts are modified or deleted. "
            "Consequential actions require user approval."
        ),
    }
