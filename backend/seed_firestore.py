
from datetime import datetime, timedelta, timezone

from app.core.firestore_store import collection, get_firestore_client


def seed_collection(name: str, documents: dict[str, dict]) -> None:
    """Create demo documents without overwriting existing data."""
    db = get_firestore_client()
    batch = db.batch()

    for document_id, data in documents.items():
        reference = collection(name).document(document_id)

        if reference.get().exists:
            print(f"Skipped existing {name}/{document_id}")
            continue

        batch.set(reference, data)
        print(f"Prepared {name}/{document_id}")

    batch.commit()


def seed_demo_data() -> None:
    now = datetime.now(timezone.utc)

    seed_collection(
        "users",
        {
            "1": {
                "name": "Demo User",
                "email": "demo@privora.test",
                "created_at": now,
            }
        },
    )

    seed_collection(
        "services",
        {
            "1": {
                "name": "GitHub",
                "website": "https://github.com",
                "purpose": "Code hosting and collaboration",
            },
            "2": {
                "name": "LinkedIn",
                "website": "https://www.linkedin.com",
                "purpose": "Professional networking",
            },
            "3": {
                "name": "Example Service",
                "website": "https://example.com",
                "purpose": "Synthetic demonstration service",
            },
        },
    )

    seed_collection(
        "accounts",
        {
            "1": {
                "user_id": 1,
                "service_id": 1,
                "status": "ACTIVE",
                "last_activity": now - timedelta(days=150),
                "created_at": now,
            },
            "2": {
                "user_id": 1,
                "service_id": 2,
                "status": "ACTIVE",
                "last_activity": now - timedelta(days=10),
                "created_at": now,
            },
            "3": {
                "user_id": 1,
                "service_id": 3,
                "status": "UNKNOWN",
                "last_activity": None,
                "created_at": now,
            },
        },
    )

    seed_collection(
        "data_records",
        {
            "1": {
                "account_id": 1,
                "category": "Email",
                "description": "Email address associated with the account",
                "created_at": now,
            },
            "2": {
                "account_id": 2,
                "category": "Professional profile",
                "description": "Professional information associated with the account",
                "created_at": now,
            },
        },
    )

    seed_collection("policies", {})
    seed_collection("privacy_actions", {})
    seed_collection("audit_logs", {})

    print("\nFirestore demo data seeding complete.")


if __name__ == "__main__":
    seed_demo_data()
