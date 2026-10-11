import pytest

from ..security.sanitizer import DataSanitizer


@pytest.fixture
def sanitizer() -> DataSanitizer:
    return DataSanitizer()


def test_sanitize_email(sanitizer: DataSanitizer) -> None:
    text = "Contact me at nandana@example.com"

    result = sanitizer.sanitize_text(text)

    assert "nandana@example.com" not in result
    assert "[EMAIL]" in result


def test_sanitize_phone_number(sanitizer: DataSanitizer) -> None:
    text = "My phone number is +91 98765 43210"

    result = sanitizer.sanitize_text(text)

    assert "98765" not in result
    assert "[PHONE]" in result


def test_sanitize_date_of_birth(sanitizer: DataSanitizer) -> None:
    text = "Date of birth: 23/09/2005"

    result = sanitizer.sanitize_text(text)

    assert "23/09/2005" not in result
    assert "[DATE]" in result


def test_sanitize_multiple_pii_values(
    sanitizer: DataSanitizer,
) -> None:
    text = (
        "Email: nandana@example.com, "
        "Phone: +91 98765 43210, "
        "DOB: 23/09/2005"
    )

    result = sanitizer.sanitize_text(text)

    assert "nandana@example.com" not in result
    assert "98765" not in result
    assert "23/09/2005" not in result

    assert "[EMAIL]" in result
    assert "[PHONE]" in result
    assert "[DATE]" in result


def test_sanitize_record_keeps_allowed_fields(
    sanitizer: DataSanitizer,
) -> None:
    record = {
        "service_name": "GitHub",
        "domain": "github.com",
        "relationship": "development",
        "source": "email",
        "email": "nandana@example.com",
        "phone": "+91 98765 43210",
    }

    result = sanitizer.sanitize_record(
        record,
        allowed_fields=[
            "service_name",
            "domain",
            "relationship",
            "source",
        ],
    )

    assert result == {
        "service_name": "GitHub",
        "domain": "github.com",
        "relationship": "development",
        "source": "email",
    }

    assert "email" not in result
    assert "phone" not in result


def test_sanitize_record_sanitizes_string_values(
    sanitizer: DataSanitizer,
) -> None:
    record = {
        "service_name": "GitHub",
        "description": "Account email: nandana@example.com",
    }

    result = sanitizer.sanitize_record(
        record,
        allowed_fields=[
            "service_name",
            "description",
        ],
    )

    assert result["service_name"] == "GitHub"
    assert result["description"] == "Account email: [EMAIL]"


def test_sanitize_record_does_not_modify_original(
    sanitizer: DataSanitizer,
) -> None:
    record = {
        "service_name": "GitHub",
        "description": "Email: nandana@example.com",
    }

    sanitizer.sanitize_record(
        record,
        allowed_fields=[
            "service_name",
            "description",
        ],
    )

    assert record["description"] == "Email: nandana@example.com"