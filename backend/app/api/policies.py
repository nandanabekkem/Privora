from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Policy, User


router = APIRouter(
    prefix="/policies",
    tags=["User Policy Management"],
)


class PolicyCreate(BaseModel):
    policy_type: str = Field(min_length=1, max_length=100)
    policy_text: str = Field(min_length=1, max_length=2000)

    @field_validator("policy_type", "policy_text")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("This field cannot be empty")

        return value


def get_policy_response(policy: Policy) -> dict:
    return {
        "id": policy.id,
        "user_id": policy.user_id,
        "policy_type": policy.policy_type,
        "policy_text": policy.policy_text,
        "created_at": policy.created_at,
    }


@router.get("/{user_id}")
def get_user_policies(
    user_id: int,
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

    policies = (
        db.query(Policy)
        .filter(Policy.user_id == user_id)
        .order_by(Policy.id)
        .all()
    )

    return {
        "user_id": user_id,
        "policy_count": len(policies),
        "policies": [
            get_policy_response(policy)
            for policy in policies
        ],
    }


@router.post("/{user_id}", status_code=201)
def create_user_policy(
    user_id: int,
    payload: PolicyCreate,
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

    policy = Policy(
        user_id=user_id,
        policy_type=payload.policy_type,
        policy_text=payload.policy_text,
    )

    db.add(policy)
    db.commit()
    db.refresh(policy)

    return {
        "message": "Privacy policy created successfully",
        "policy": get_policy_response(policy),
    }
