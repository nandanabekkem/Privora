from datetime import datetime

import pytest

from ..sources.email.parser import EmailParser


@pytest.fixture
def parser() -> EmailParser:
    return EmailParser()


def test_parse_account_related_email(
    parser: EmailParser,
) -> None:
    email = {
        "subject": "Welcome to Internshala",
        "sender": "hello@internshala.com",
        "body": (
            "Your account has been created successfully. "
            "Your internship application is now active."
        ),
        "timestamp": "2026-09-01T10:30:00",
    }

    result = parser.parse(email)

    assert result is not None
    assert result["domain"] == "internshala.com"
    assert result["subject"] == "Welcome to Internshala"
    assert result["sender"] == "hello@internshala.com"
    assert result["timestamp"] == datetime(
        2026,
        9,
        1,
        10,
        30,
    )


def test_parse_detects_relationship(
    parser: EmailParser,
) -> None:
    email = {
        "subject": "Internship application received",
        "sender": "notifications@internshala.com",
        "body": (
            "We received your internship application "
            "and resume."
        ),
    }

    result = parser.parse(email)

    assert result is not None
    assert result["relationship"] == "internship"


def test_parse_detects_data_categories(
    parser: EmailParser,
) -> None:
    email = {
        "subject": "Application submitted",
        "sender": "notifications@example.com",
        "body": (
            "Your resume, phone number, college details "
            "and certificate have been added to your profile."
        ),
    }

    result = parser.parse(email)

    assert result is not None

    assert "professional" in result["data_categories"]
    assert "contact" in result["data_categories"]
    assert "academic" in result["data_categories"]


def test_parse_education_email(
    parser: EmailParser,
) -> None:
    email = {
        "subject": "Welcome to Coursera",
        "sender": "hello@coursera.org",
        "body": (
            "You are enrolled in a course. "
            "Your student profile and certificate are available."
        ),
    }

    result = parser.parse(email)

    assert result is not None
    assert result["domain"] == "coursera.org"
    assert result["relationship"] == "education"
    assert "academic" in result["data_categories"]


def test_ignore_irrelevant_email(
    parser: EmailParser,
) -> None:
    email = {
        "subject": "Weekend Sale",
        "sender": "offers@shop.com",
        "body": "Get 50% off this weekend.",
        "timestamp": "2026-09-01T10:30:00",
    }

    result = parser.parse(email)

    assert result is None


def test_extract_domain_from_sender(
    parser: EmailParser,
) -> None:
    email = {
        "subject": "Verify your email",
        "sender": "noreply@github.com",
        "body": "Please verify your email address.",
    }

    result = parser.parse(email)

    assert result is not None
    assert result["domain"] == "github.com"


def test_extract_domain_from_body(
    parser: EmailParser,
) -> None:
    email = {
        "subject": "Your account",
        "sender": "notifications@service.com",
        "body": (
            "Visit https://www.example-platform.com/account "
            "to manage your account."
        ),
    }

    result = parser.parse(email)

    assert result is not None
    assert result["domain"] == "service.com"


def test_parse_many_filters_irrelevant_emails(
    parser: EmailParser,
) -> None:
    emails = [
        {
            "subject": "Welcome to GitHub",
            "sender": "noreply@github.com",
            "body": "Your account has been created.",
        },
        {
            "subject": "Your order has shipped",
            "sender": "orders@shop.com",
            "body": "Your package is on the way.",
        },
        {
            "subject": "Password reset",
            "sender": "security@coursera.org",
            "body": "A password reset was requested.",
        },
    ]

    results = parser.parse_many(emails)

    assert len(results) == 2
    assert results[0]["domain"] == "github.com"
    assert results[1]["domain"] == "coursera.org"


def test_invalid_timestamp_returns_none(
    parser: EmailParser,
) -> None:
    email = {
        "subject": "Welcome to GitHub",
        "sender": "noreply@github.com",
        "body": "Your account has been created.",
        "timestamp": "not-a-valid-date",
    }

    result = parser.parse(email)

    assert result is not None
    assert result["timestamp"] is None


def test_missing_domain_returns_none(
    parser: EmailParser,
) -> None:
    email = {
        "subject": "Welcome",
        "sender": "hello",
        "body": "Your account has been created.",
    }

    result = parser.parse(email)

    assert result is None