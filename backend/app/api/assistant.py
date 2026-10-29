from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field, field_validator

from ..core.authentication import (
    authorize_user_path,
    canonical_user_id,
    get_current_user,
    validate_numeric_user_path,
)
from ..core.firestore_store import collection, get_document, list_by_field
from ..services.privacy_analysis import generate_account_answer
from ..services.rules_engine import evaluate_account
from ..services.service_metadata import metadata_for_service


router = APIRouter(prefix="/assistant", tags=["Account Assistant"])


class ChatMessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message cannot be blank")
        return value.strip()


def _owned_account(user_id: int | str, account_id: str) -> dict:
    account = get_document("accounts", account_id)
    if account is None or str(account.get("user_id")) != str(user_id):
        raise HTTPException(status_code=404, detail="Account not found for this user")
    return account


def _messages(user_id: int | str, account_id: str) -> list[dict]:
    messages = list_by_field("assistant_messages", "user_id", user_id)
    messages.extend(list_by_field("assistant_messages", "user_id", str(user_id)))
    unique = {message["id"]: message for message in messages}
    relevant = [
        message for message in unique.values()
        if str(message.get("account_id")) == str(account_id)
    ]
    relevant.sort(key=lambda item: (item.get("created_at") or datetime.min.replace(tzinfo=timezone.utc), item["id"]))
    return relevant[-100:]


@router.get("/{user_id}/accounts/{account_id}/messages")
def get_account_messages(
    user_id: str,
    account_id: str = Path(min_length=1),
    claims: dict = Depends(get_current_user),
):
    validate_numeric_user_path(user_id)
    user = authorize_user_path(user_id, claims)
    owned_user_id = canonical_user_id(user)
    _owned_account(owned_user_id, account_id)
    return {"account_id": account_id, "messages": _messages(owned_user_id, account_id)}


@router.post("/{user_id}/accounts/{account_id}/messages")
def send_account_message(
    payload: ChatMessageCreate,
    user_id: str,
    account_id: str = Path(min_length=1),
    claims: dict = Depends(get_current_user),
):
    validate_numeric_user_path(user_id)
    user = authorize_user_path(user_id, claims)
    owned_user_id = canonical_user_id(user)
    account = _owned_account(owned_user_id, account_id)
    records = list_by_field("data_records", "account_id", account_id)
    if str(account_id).isdigit():
        records += list_by_field("data_records", "account_id", int(account_id))
    records = list({record["id"]: record for record in records}.values())
    service = get_document("services", account["service_id"]) if account.get("service_id") else None
    context = {
        **account,
        "service_name": (service or {}).get("name", account.get("service_name", "Unknown service")),
        "website": (service or {}).get("website", account.get("website")),
        "purpose": (service or {}).get("purpose", account.get("purpose")),
    }
    metadata = metadata_for_service(
        name=context["service_name"],
        domain=account.get("domain"),
        website=context["website"],
    )
    if metadata:
        context["purpose"] = metadata["purpose"]
        context["purpose_source_url"] = metadata["purpose_source_url"]
    context["evidence_confidence"] = (
        "low" if context.get("discovery_source") == "gmail" else "unknown"
    )
    context["evidence_note"] = (
        "Inferred from Gmail headers; this does not verify an account or recent service activity."
        if context.get("discovery_source") == "gmail"
        else "Confidence is not available for this stored inventory record."
    )
    last_activity = account.get("last_activity")
    if isinstance(last_activity, str):
        try:
            last_activity = datetime.fromisoformat(last_activity.replace("Z", "+00:00"))
        except ValueError:
            last_activity = None
    policies = list_by_field("policies", "user_id", owned_user_id)
    policies.extend(list_by_field("policies", "user_id", str(owned_user_id)))
    unique_policies = {item["id"]: item for item in policies}
    local_recommendation = evaluate_account(
        SimpleNamespace(
            id=account_id,
            last_activity=last_activity,
            data_records=[
                SimpleNamespace(
                    category=record.get("category"),
                    description=record.get("description"),
                )
                for record in records
            ],
            service=SimpleNamespace(name=context["service_name"], website=context["website"]),
        ),
        policies=[
            SimpleNamespace(
                id=item["id"],
                policy_type=item.get("policy_type", ""),
                policy_text=item.get("policy_text", ""),
            )
            for item in unique_policies.values()
        ],
    )
    context["local_recommendation"] = local_recommendation["recommendation"]
    context["local_recommendation_reason"] = local_recommendation["reason"]
    try:
        generated = generate_account_answer(
            context,
            records,
            payload.message,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Local account response could not be generated") from exc

    now = datetime.now(timezone.utc)
    assistant_time = now + timedelta(microseconds=1)
    messages = collection("assistant_messages")
    user_ref = messages.document()
    assistant_ref = messages.document()
    user_ref.set({
        "user_id": owned_user_id,
        "account_id": account_id,
        "role": "user",
        "content": payload.message,
        "created_at": now,
    })
    assistant_ref.set({
        "user_id": owned_user_id,
        "account_id": account_id,
        "role": "assistant",
        "content": generated["answer"],
        "mode": generated["mode"],
        "created_at": assistant_time,
    })
    return {
        "account_id": account_id,
        "mode": generated["mode"],
        "messages": [
            {"id": user_ref.id, "role": "user", "content": payload.message, "created_at": now},
            {"id": assistant_ref.id, "role": "assistant", "content": generated["answer"], "mode": generated["mode"], "created_at": assistant_time},
        ],
    }
