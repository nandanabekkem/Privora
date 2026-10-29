
from fastapi import APIRouter, Depends, HTTPException

from ..core.authentication import (
    authorize_user_path,
    canonical_user_id,
    get_current_user,
    validate_numeric_user_path,
)
from ..core.firestore_store import get_document, list_by_field
from ..services.service_metadata import metadata_for_service


router = APIRouter(
    prefix="/data-map",
    tags=["Personal Data Map"],
)


def numeric_id(value):
    return int(value) if str(value).isdigit() else value


@router.get("/{user_id}")
def get_data_map(user_id: str, claims: dict = Depends(get_current_user)):
    validate_numeric_user_path(user_id)

    user = authorize_user_path(user_id, claims)
    owned_user_id = canonical_user_id(user)

    accounts = list_by_field("accounts", "user_id", owned_user_id)

    # Also support documents that store foreign keys as strings.
    accounts.extend(list_by_field("accounts", "user_id", str(owned_user_id)))

    # Deduplicate documents in case both queries return the same account.
    unique_accounts = {account["id"]: account for account in accounts}
    accounts = sorted(
        unique_accounts.values(),
        key=lambda account: (
            0 if str(account["id"]).isdigit() else 1,
            int(account["id"]) if str(account["id"]).isdigit()
            else str(account["id"]),
        ),
    )

    data_map = []

    for account in accounts:
        service_id = account.get("service_id")
        service = (
            get_document("services", service_id)
            if service_id is not None
            else None
        )

        if service is None:
            service = {
                "name": account.get("service_name", "Unknown service"),
                "website": account.get("website"),
                "purpose": account.get("purpose"),
            }
        metadata = metadata_for_service(
            name=service.get("name", account.get("service_name")),
            domain=account.get("domain"),
            website=service.get("website", account.get("website")),
        ) or {}

        data_records = list_by_field(
            "data_records", "account_id", numeric_id(account["id"])
        )
        data_records.extend(
            list_by_field("data_records", "account_id", str(account["id"]))
        )

        unique_records = {
            record["id"]: record for record in data_records
        }

        records = [
            {
                "category": record.get("category"),
                "description": record.get("description"),
            }
            for record in unique_records.values()
        ]

        data_map.append(
            {
                "account_id": numeric_id(account["id"]),
                "service": service.get("name", "Unknown service"),
                "domain": account.get("domain"),
                "website": service.get("website"),
                "purpose": metadata.get("purpose") or service.get("purpose") or account.get("purpose"),
                "purpose_source_url": metadata.get("purpose_source_url"),
                "status": account.get("status", "UNKNOWN"),
                "last_activity": account.get("last_activity"),
                "last_evidence_at": account.get("last_evidence_at"),
                "discovery_source": account.get("discovery_source"),
                "evidence_confidence": (
                    "low" if account.get("discovery_source") == "gmail" else "unknown"
                ),
                "evidence_note": (
                    "Inferred from Gmail headers; this does not verify an account or recent service activity."
                    if account.get("discovery_source") == "gmail"
                    else "Confidence is not available for this stored inventory record."
                ),
                "data_records": records,
                "data_record_count": len(records),
            }
        )

    return {
        "user_id": owned_user_id,
        "account_count": len(data_map),
        "accounts": data_map,
    }
