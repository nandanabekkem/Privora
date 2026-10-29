
from datetime import datetime, timezone
from typing import Any

from .firebase import get_firestore_client
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.firestore_v1 import transactional

COLLECTIONS = {
    "users": "users",
    "services": "services",
    "accounts": "accounts",
    "data_records": "data_records",
    "policies": "policies",
    "privacy_actions": "privacy_actions",
    "audit_logs": "audit_logs",
    "gmail_oauth_states": "gmail_oauth_states",
    "gmail_tokens": "gmail_tokens",
    "assistant_messages": "assistant_messages",
}


def collection(name: str):
    if name not in COLLECTIONS:
        raise ValueError(f"Unsupported collection: {name}")

    return get_firestore_client().collection(COLLECTIONS[name])


def get_document(name: str, document_id: str | int) -> dict | None:
    snapshot = collection(name).document(str(document_id)).get()

    if not snapshot.exists:
        return None

    return {"id": snapshot.id, **(snapshot.to_dict() or {})}


def list_documents(name: str) -> list[dict]:
    return [
        {"id": snapshot.id, **(snapshot.to_dict() or {})}
        for snapshot in collection(name).stream()
    ]


def list_by_field(name: str, field: str, value: Any) -> list[dict]:
    query = collection(name).where(
        filter=FieldFilter(field, "==", value)
    )

    return [
        {"id": snapshot.id, **(snapshot.to_dict() or {})}
        for snapshot in query.stream()
    ]


def create_document(name: str, data: dict) -> dict:
    """Create a document using a numeric ID stored as its document ID."""
    db = get_firestore_client()
    counter_ref = db.collection("_counters").document(name)
    target_collection = collection(name)

    # Allocate an ID transactionally, skipping IDs already in use.
    transaction = db.transaction()

    @__import__("google.cloud.firestore_v1", fromlist=["transactional"]).transactional
    def allocate_id(tx):
        counter_snapshot = counter_ref.get(transaction=tx)
        current = (
            counter_snapshot.to_dict().get("value", 0)
            if counter_snapshot.exists
            else 0
        )

        next_id = int(current) + 1

        while target_collection.document(str(next_id)).get(transaction=tx).exists:
            next_id += 1

        tx.set(counter_ref, {"value": next_id})
        return next_id

    document_id = allocate_id(transaction)

    payload = dict(data)
    payload.setdefault("created_at", datetime.now(timezone.utc))

    target_collection.document(str(document_id)).set(payload)

    return {"id": document_id, **payload}


def update_document(
    name: str,
    document_id: str | int,
    data: dict,
) -> dict | None:
    reference = collection(name).document(str(document_id))
    snapshot = reference.get()

    if not snapshot.exists:
        return None

    reference.update(data)
    updated = reference.get()

    return {"id": updated.id, **(updated.to_dict() or {})}


def create_action_with_audit(
    user_id: int | str,
    account_id: int | str,
    action_type: str,
    description: str,
    metadata: dict | None = None,
) -> dict:
    """Atomically create a pending privacy action and its audit entry."""
    db = get_firestore_client()
    actions = collection("privacy_actions")
    logs = collection("audit_logs")
    action_ref = actions.document()
    log_ref = logs.document()

    @transactional
    def write_records(transaction):
        action_data = {
            "user_id": user_id,
            "account_id": account_id,
            "action_type": action_type,
            "description": description,
            "status": "PENDING",
            "requires_approval": True,
            "created_at": datetime.now(timezone.utc),
            "reviewed_at": None,
        }
        action_data.update(metadata or {})
        transaction.set(
            action_ref,
            action_data,
        )
        transaction.set(
            log_ref,
            {
                "user_id": user_id,
                "privacy_action_id": action_ref.id,
                "event_type": "ACTION_CREATED",
                "details": (
                    f"Privacy action {action_ref.id} was created "
                    "and is pending user approval."
                ),
                "created_at": datetime.now(timezone.utc),
            },
        )

    write_records(db.transaction())

    action = action_ref.get()
    return {"id": action.id, **(action.to_dict() or {})}


def review_action_with_audit(
    user_id: int | str,
    action_id: str | int,
    decision: str,
) -> dict:
    """Atomically review a pending action and create its audit entry."""
    db = get_firestore_client()
    action_ref = collection("privacy_actions").document(str(action_id))
    log_ref = collection("audit_logs").document()
    reviewed_at = datetime.now(timezone.utc)

    @transactional
    def write_review(transaction):
        snapshot = action_ref.get(transaction=transaction)

        if not snapshot.exists:
            return {"error": "not_found"}

        action = snapshot.to_dict() or {}

        if str(action.get("user_id")) != str(user_id):
            return {"error": "not_found"}

        if action.get("status") != "PENDING":
            return {"error": "not_pending"}

        new_status = "APPROVED" if decision == "APPROVE" else "REJECTED"
        updates = {
            "status": new_status,
            "reviewed_at": reviewed_at,
        }
        if action.get("action_type") == "DELETE_REQUEST_DRAFT":
            updates["request_status"] = (
                "APPROVED_NOT_SENT"
                if decision == "APPROVE"
                else "REJECTED"
            )

        transaction.update(
            action_ref,
            updates,
        )

        transaction.set(
            log_ref,
            {
                "user_id": user_id,
                "privacy_action_id": str(action_id),
                "event_type": f"ACTION_{decision}",
                "details": (
                    f"Privacy action {action_id} was "
                    f"{new_status.lower()} by the user."
                ),
                "created_at": reviewed_at,
            },
        )

        return {
            "id": str(action_id),
            "status": new_status,
            "reviewed_at": reviewed_at,
        }

    return write_review(db.transaction())
