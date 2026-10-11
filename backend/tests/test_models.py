from app.core.database import Base
import app.models


def test_all_models_are_registered():
    expected_tables = {
        "users",
        "services",
        "accounts",
        "data_records",
        "policies",
        "privacy_actions",
    }

    assert expected_tables.issubset(
        set(Base.metadata.tables.keys())
    )