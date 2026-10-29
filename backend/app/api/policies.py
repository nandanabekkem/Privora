
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from ..core.authentication import (
    authorize_user_path,
    canonical_user_id,
    get_current_user,
    validate_numeric_user_path,
)
from ..core.firestore_store import (
    create_document,
    get_document,
    list_by_field,
)


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


def numeric_id(value):
    return int(value) if str(value).isdigit() else value


def get_policy_response(policy: dict) -> dict:
    return {
        "id": numeric_id(policy["id"]),
        "user_id": numeric_id(policy["user_id"]),
        "policy_type": policy.get("policy_type"),
        "policy_text": policy.get("policy_text"),
        "created_at": policy.get("created_at"),
    }


def get_user_policies(user_id: int | str) -> list[dict]:
    policies = list_by_field("policies", "user_id", user_id)
    policies.extend(
        list_by_field("policies", "user_id", str(user_id))
    )

    unique = {policy["id"]: policy for policy in policies}

    return sorted(
        unique.values(),
        key=lambda policy: (
            0 if str(policy["id"]).isdigit() else 1,
            int(policy["id"]) if str(policy["id"]).isdigit()
            else str(policy["id"]),
        ),
    )


@router.get("/{user_id}")
def get_user_policies_endpoint(
    user_id: str,
    claims: dict = Depends(get_current_user),
):
    validate_numeric_user_path(user_id)

    user = authorize_user_path(user_id, claims)
    owned_user_id = canonical_user_id(user)

    policies = get_user_policies(owned_user_id)

    return {
        "user_id": owned_user_id,
        "policy_count": len(policies),
        "policies": [
            get_policy_response(policy) for policy in policies
        ],
    }


@router.post("/{user_id}", status_code=201)
def create_user_policy(
    user_id: str,
    payload: PolicyCreate,
    claims: dict = Depends(get_current_user),
):
    validate_numeric_user_path(user_id)

    user = authorize_user_path(user_id, claims)
    owned_user_id = canonical_user_id(user)

    policy = create_document(
        "policies",
        {
            "user_id": owned_user_id,
            "policy_type": payload.policy_type,
            "policy_text": payload.policy_text,
            "created_at": datetime.now(timezone.utc),
        },
    )

    return {
        "message": "Privacy policy created successfully",
        "policy": get_policy_response(policy),
    }
