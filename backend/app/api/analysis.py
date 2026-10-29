from fastapi import APIRouter, Depends, HTTPException, Path

from ..core.authentication import (
    authorize_user_path,
    canonical_user_id,
    get_current_user,
    validate_numeric_user_path,
)
from ..core.firestore_store import get_document, list_by_field
from ..services.privacy_analysis import analyze_stored_data, generate_account_answer
from ..services.service_metadata import metadata_for_service


router = APIRouter(prefix="/analysis", tags=["Privacy Analysis"])


def _account_context(account: dict) -> tuple[dict, list[dict]]:
    account_id = account["id"]
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
    return context, records


@router.post("/{user_id}/accounts/{account_id}")
def analyze_account(
    user_id: str,
    account_id: str = Path(min_length=1),
    claims: dict = Depends(get_current_user),
):
    validate_numeric_user_path(user_id)
    user = authorize_user_path(user_id, claims)
    owned_user_id = canonical_user_id(user)
    account = get_document("accounts", account_id)
    if account is None or str(account.get("user_id")) != str(owned_user_id):
        raise HTTPException(status_code=404, detail="Account not found for this user")

    context, records = _account_context(account)
    sensitivity = analyze_stored_data(records)
    try:
        result = generate_account_answer(
            context,
            records,
            "Explain the service purpose and assess the sensitivity of the recorded data. Distinguish catalog information from inference.",
            response_style="privacy_analysis",
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Local account analysis could not be generated") from exc

    return {
        "account_id": account_id,
        "service": context["service_name"],
        "website": context["website"],
        "catalog_purpose": context["purpose"],
        "purpose_source_url": context.get("purpose_source_url"),
        "discovery_source": context.get("discovery_source") or "unknown",
        "evidence_confidence": context["evidence_confidence"],
        "last_evidence_at": context.get("last_evidence_at"),
        "evidence_note": context["evidence_note"],
        "sensitivity": sensitivity,
        "analysis_mode": result["mode"],
        "explanation": result["answer"],
        "fallback_reason": result.get("fallback_reason"),
        "limitations": "The service purpose may come from Privora's catalog. Data categories are recorded or inferred; this is not a provider-side audit.",
    }
