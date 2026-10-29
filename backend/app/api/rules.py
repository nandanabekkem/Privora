
from fastapi import APIRouter, Depends, HTTPException, Query
from types import SimpleNamespace

from ..core.authentication import (
    authorize_user_path,
    canonical_user_id,
    get_current_user,
    validate_numeric_user_path,
)
from ..core.firestore_store import (
    get_document,
    list_by_field,
)
from ..services.rules_engine import evaluate_account
from ..services.privacy_analysis import analyze_stored_data


router = APIRouter(
    prefix="/rules",
    tags=["Privacy Rules Engine"],
)


def numeric_id(value):
    return int(value) if str(value).isdigit() else value


def get_user_accounts(user_id: int | str) -> list[dict]:
    accounts = list_by_field("accounts", "user_id", user_id)
    accounts.extend(list_by_field("accounts", "user_id", str(user_id)))

    unique = {account["id"]: account for account in accounts}

    return sorted(
        unique.values(),
        key=lambda item: (
            0 if str(item["id"]).isdigit() else 1,
            int(item["id"]) if str(item["id"]).isdigit()
            else str(item["id"]),
        ),
    )


@router.get("/{user_id}")
def evaluate_user_accounts(
    user_id: str,
    days: int = Query(default=90, ge=1, le=3650),
    claims: dict = Depends(get_current_user),
):
    validate_numeric_user_path(user_id)

    user = authorize_user_path(user_id, claims)
    owned_user_id = canonical_user_id(user)

    policies = list_by_field("policies", "user_id", owned_user_id)
    policies.extend(list_by_field("policies", "user_id", str(owned_user_id)))
    policies = list({item["id"]: item for item in policies}.values())

    recommendations = []

    for account in get_user_accounts(owned_user_id):
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
            }

        records = list_by_field(
            "data_records", "account_id", numeric_id(account["id"])
        )
        records.extend(
            list_by_field("data_records", "account_id", str(account["id"]))
        )
        records = list({item["id"]: item for item in records}.values())

        # Adapt Firestore dictionaries to the attribute interface expected
        # by the existing rules engine. The engine itself stays unchanged.
        account_obj = SimpleNamespace(
            id=numeric_id(account["id"]),
            last_activity=account.get("last_activity"),
            data_records=[
                SimpleNamespace(
                    category=record.get("category"),
                    description=record.get("description"),
                )
                for record in records
            ],
            service=SimpleNamespace(
                name=service.get("name", "Unknown service"),
                website=service.get("website"),
            ),
        )

        policy_objs = [
            SimpleNamespace(
                id=numeric_id(policy["id"]),
                policy_type=policy.get("policy_type", ""),
                policy_text=policy.get("policy_text", ""),
            )
            for policy in policies
        ]

        recommendation = evaluate_account(
            account_obj,
            days_threshold=days,
            policies=policy_objs,
        )
        analysis = analyze_stored_data(records)
        stored_categories = sorted({
            str(record.get("category") or "").strip().lower()
            for record in records
            if record.get("category") and record.get("source") != "gmail_header_inference"
        })
        inferred_categories = sorted({
            str(record.get("category") or "").strip().lower()
            for record in records
            if record.get("category") and record.get("source") == "gmail_header_inference"
        })
        source = str(account.get("discovery_source") or "unknown")
        evidence_confidence = "low" if source == "gmail" else "unknown"
        last_evidence_at = account.get("last_evidence_at")
        # Keep the deterministic engine's first rationale sentence authoritative;
        # expose evidence and category context in separate concise fields.
        recommendation["reason"] = recommendation["reason"].split(". ", 1)[0].rstrip(".") + "."
        recorded_context = (
            f"Recorded categories: {', '.join(stored_categories)}"
            if stored_categories
            else "No categories recorded"
        )
        inferred_context = (
            f"Inferred categories from Gmail metadata: {', '.join(inferred_categories)}"
            if inferred_categories and source == "gmail"
            else "No categories inferred from Gmail metadata"
            if source == "gmail"
            else f"Inferred categories: {', '.join(inferred_categories)}"
            if inferred_categories
            else "No categories inferred"
        )
        recommendation["data_context"] = f"{recorded_context}; {inferred_context}."
        recommendation["evidence_note"] = (
            "Gmail metadata alone does not verify account ownership or activity."
            if source == "gmail"
            else "Synthetic sample; this is not a real account discovery."
            if source == "synthetic"
            else None
        )
        # Retain the existing response fields for API compatibility; this
        # recommendation is determined by local rules and has no AI add-on.
        recommendation["ai_explanation"] = None
        recommendation["analysis_mode"] = "rules"
        recommendation["fallback_reason"] = None
        recommendation["data_categories"] = analysis["categories"]
        recommendation["sensitive_categories"] = analysis["sensitive_categories"]
        recommendation["discovery_source"] = source
        recommendation["evidence_confidence"] = evidence_confidence
        recommendation["last_evidence_at"] = last_evidence_at
        recommendations.append(recommendation)

    return {
        "user_id": owned_user_id,
        "days_threshold": days,
        "saved_policy_count": len(policies),
        "account_count": len(recommendations),
        "recommendation_count": len(recommendations),
        "recommendations": recommendations,
        "note": (
            "Recommendations use recorded database data and saved policies. "
            "They are suggestions, not proof that an account is unused. "
            "No external accounts are modified or deleted. "
            "Consequential actions require user approval."
        ),
    }
