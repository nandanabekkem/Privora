
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Account, PrivacyAction, User


router = APIRouter(
    prefix="/privacy-actions",
    tags=["Privacy Actions"],
)


class PrivacyActionCreate(BaseModel):
    account_id: int = Field(gt=0)
    action_type: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=2000)

    @field_validator("action_type", "description")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "This field cannot be empty or contain only spaces"
            )

        return value


class PrivacyActionReview(BaseModel):
    decision: str = Field(min_length=1, max_length=20)

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, value: str) -> str:
        value = value.strip().upper()

        if value not in {"APPROVE", "REJECT"}:
            raise ValueError("Decision must be APPROVE or REJECT")

        return value


@router.post("/{user_id}", status_code=201)
def create_privacy_action(
    user_id: int = Path(gt=0),
    payload: PrivacyActionCreate = ...,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    account = (
        db.query(Account)
        .filter(
            Account.id == payload.account_id,
            Account.user_id == user_id,
        )
        .first()
    )

    if account is None:
        raise HTTPException(
            status_code=404,
            detail="Account not found for this user",
        )

    action = PrivacyAction(
        user_id=user_id,
        account_id=account.id,
        action_type=payload.action_type,
        description=payload.description,
        status="PENDING",
        requires_approval=True,
    )

    try:
        db.add(action)
        db.commit()
        db.refresh(action)
    except Exception:
        db.rollback()
        raise

    return {
        "id": action.id,
        "user_id": action.user_id,
        "account_id": action.account_id,
        "action_type": action.action_type,
        "description": action.description,
        "status": action.status,
        "requires_approval": action.requires_approval,
        "created_at": action.created_at,
        "message": "Proposed action created. User approval is required.",
    }


@router.get("/{user_id}")
def list_privacy_actions(
    user_id: int = Path(gt=0),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    actions = (
        db.query(PrivacyAction)
        .filter(PrivacyAction.user_id == user_id)
        .order_by(PrivacyAction.id.desc())
        .all()
    )

    return {
        "user_id": user_id,
        "count": len(actions),
        "actions": [
            {
                "id": action.id,
                "account_id": action.account_id,
                "action_type": action.action_type,
                "description": action.description,
                "status": action.status,
                "requires_approval": action.requires_approval,
                "created_at": action.created_at,
                "reviewed_at": action.reviewed_at,
            }
            for action in actions
        ],
    }


@router.post("/{user_id}/{action_id}/review")
def review_privacy_action(
    user_id: int = Path(gt=0),
    action_id: int = Path(gt=0),
    payload: PrivacyActionReview = ...,
    db: Session = Depends(get_db),
):
    decision = payload.decision

    action = (
        db.query(PrivacyAction)
        .filter(
            PrivacyAction.id == action_id,
            PrivacyAction.user_id == user_id,
        )
        .first()
    )

    if action is None:
        raise HTTPException(
            status_code=404,
            detail="Privacy action not found",
        )

    if action.status != "PENDING":
        raise HTTPException(
            status_code=409,
            detail="Only pending actions can be reviewed",
        )

    action.status = (
        "APPROVED" if decision == "APPROVE" else "REJECTED"
    )
    action.reviewed_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(action)
    except Exception:
        db.rollback()
        raise

    return {
        "id": action.id,
        "status": action.status,
        "reviewed_at": action.reviewed_at,
        "message": (
            "Approval recorded. No external account action was executed."
            if decision == "APPROVE"
            else "Rejection recorded. No external account action was executed."
        ),
    }
