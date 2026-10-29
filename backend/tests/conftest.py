
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import google.cloud.firestore_v1 as firestore_v1


# Keep Firestore's transaction decorator from making real network calls.
# The mock transaction below applies writes directly to isolated memory.
def _mock_transactional(function):
    return function


firestore_v1.transactional = _mock_transactional


class MockSnapshot:
    def __init__(self, document_id, data):
        self.id = document_id
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return self._data.copy() if self._data is not None else None


class MockDocumentReference:
    def __init__(self, database, collection_name, document_id):
        self.database = database
        self.collection_name = collection_name
        self.id = str(document_id)

    def get(self, transaction=None):
        data = self.database.data[self.collection_name].get(self.id)
        return MockSnapshot(self.id, data)

    def set(self, data):
        self.database.data[self.collection_name][self.id] = dict(data)

    def update(self, data):
        current = self.database.data[self.collection_name].get(self.id)
        if current is None:
            raise KeyError(f"Document {self.id} does not exist")
        current.update(data)

    def delete(self):
        self.database.data[self.collection_name].pop(self.id, None)


class MockQuery:
    def __init__(self, database, collection_name, filters=None):
        self.database = database
        self.collection_name = collection_name
        self.filters = filters or []

    def where(self, field=None, op=None, value=None, *, filter=None):
        if filter is not None:
            self.filters.append(
                (filter.field_path, filter.op_string, filter.value)
            )
        else:
            self.filters.append((field, op, value))
        return self

    def stream(self):
        documents = self.database.data[self.collection_name]
        for document_id, data in documents.items():
            matches = all(
                op == "==" and data.get(field) == value
                for field, op, value in self.filters
            )
            if matches:
                yield MockSnapshot(document_id, data)


class MockCollection(MockQuery):
    def document(self, document_id=None):
        return MockDocumentReference(
            self.database,
            self.collection_name,
            document_id or uuid4().hex,
        )


class MockTransaction:
    def __init__(self, database):
        self.database = database

    def set(self, reference, data):
        reference.set(data)

    def update(self, reference, data):
        reference.update(data)

    def delete(self, reference):
        reference.delete()


class MockFirestore:
    def __init__(self):
        self.data = {}
        self.data["_counters"] = {}

    def collection(self, name):
        self.data.setdefault(name, {})
        return MockCollection(self, name)

    def transaction(self):
        return MockTransaction(self)


@pytest.fixture
def mock_firestore(monkeypatch):
    from app.core import firebase, firestore_store

    database = MockFirestore()

    monkeypatch.setattr(
        firebase,
        "get_firestore_client",
        lambda: database,
    )
    monkeypatch.setattr(
        firestore_store,
        "get_firestore_client",
        lambda: database,
    )

    now = datetime.now(timezone.utc)

    # Minimal demo data; each test receives a fresh database.
    database.collection("users").document("1").set({
        "name": "Test User",
        "email": "test@example.com",
        "firebase_uid": "test-user-uid",
    })

    database.collection("services").document("1").set({
        "name": "Example Service",
        "website": "https://example.com",
    })

    database.collection("accounts").document("1").set({
        "user_id": 1,
        "service_id": 1,
        "status": "ACTIVE",
        "last_activity": now - timedelta(days=150),
    })

    database.collection("data_records").document("1").set({
        "account_id": 1,
        "category": "Email",
        "description": "Email address stored by the service",
    })

    return database


@pytest.fixture
def client(mock_firestore):
    from fastapi.testclient import TestClient

    from app.core.authentication import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: {
        "uid": "test-user-uid",
        "email": "test@example.com",
        "name": "Test User",
    }
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_current_user, None)
