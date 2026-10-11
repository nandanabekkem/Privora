from datetime import datetime

import pytest

from ..pipeline.discovery_pipeline import DiscoveryPipeline
from ..sources.email.parser import EmailParser
from ..sources.email.provider import EmailProvider


@pytest.fixture
def pipeline() -> DiscoveryPipeline:
    return DiscoveryPipeline(
        email_provider=EmailProvider.synthetic(),
        parser=EmailParser(),
    )


def test_pipeline_discovers_expected_accounts(
    pipeline: DiscoveryPipeline,
) -> None:
    results = pipeline.run()

    assert len(results) == 8

    service_names = {
        result.service_name
        for result in results
    }

    assert "GitHub" in service_names
    assert "LinkedIn" in service_names
    assert "Internshala" in service_names
    assert "Coursera" in service_names
    assert "Unstop" in service_names
    assert "Devpost" in service_names
    assert "Amazon" in service_names
    assert "Example Service" in service_names


def test_pipeline_ignores_irrelevant_emails(
    pipeline: DiscoveryPipeline,
) -> None:
    results = pipeline.run()

    service_names = {
        result.service_name
        for result in results
    }

    assert "Shop" not in service_names
    assert "News" not in service_names


def test_pipeline_resolves_relationships(
    pipeline: DiscoveryPipeline,
) -> None:
    results = pipeline.run()

    relationships = {
        result.service_name: result.relationship
        for result in results
    }

    assert relationships["GitHub"] == "development"
    assert relationships["LinkedIn"] == "professional"
    assert relationships["Internshala"] == "internship"
    assert relationships["Coursera"] == "education"
    assert relationships["Unstop"] == "hackathon"
    assert relationships["Devpost"] == "hackathon"
    assert relationships["Amazon"] == "shopping"
    assert relationships["Example Service"] is None


def test_pipeline_detects_data_categories(
    pipeline: DiscoveryPipeline,
) -> None:
    results = pipeline.run()

    internshala = next(
        result
        for result in results
        if result.service_name == "Internshala"
    )

    categories = {
        category.value
        for category in internshala.data_categories
    }

    assert "professional" in categories
    assert "contact" in categories
    assert "academic" in categories


def test_pipeline_preserves_discovery_source(
    pipeline: DiscoveryPipeline,
) -> None:
    results = pipeline.run()

    assert all(
        result.source.value == "email"
        for result in results
    )


def test_pipeline_preserves_activity_timestamp(
    pipeline: DiscoveryPipeline,
) -> None:
    results = pipeline.run()

    github = next(
        result
        for result in results
        if result.service_name == "GitHub"
    )

    assert github.first_seen == datetime(
        2026,
        9,
        1,
        10,
        30,
    )

    assert github.last_activity == datetime(
        2026,
        10,
        2,
        14,
        20,
    )
    
def test_pipeline_returns_sanitized_context(
    pipeline: DiscoveryPipeline,
) -> None:
    results = pipeline.run()

    assert results

    for result in results:
        assert not hasattr(result, "sender")
        assert not hasattr(result, "email_body")


def test_pipeline_stores_identity_separately(
    pipeline: DiscoveryPipeline,
) -> None:
    results = pipeline.run()

    assert results

    github = next(
        result
        for result in results
        if result.service_name == "GitHub"
    )

    record_id = (
        f"{github.domain}:"
        f"{github.last_activity.isoformat()}"
    )

    assert pipeline.vault.exists(record_id)

    identity_data = pipeline.vault.get(record_id)

    assert identity_data is not None
    assert identity_data["sender"] == "security@github.com"


def test_pipeline_handles_empty_provider() -> None:
    pipeline = DiscoveryPipeline(
        email_provider=EmailProvider([]),
    )

    results = pipeline.run()

    assert results == []


def test_pipeline_deduplicates_same_service() -> None:
    emails = [
        {
            "subject": "Welcome to GitHub",
            "sender": "noreply@github.com",
            "body": (
                "Your GitHub account has been created. "
                "Your email is associated with your profile."
            ),
            "timestamp": "2026-01-10T10:00:00",
        },
        {
            "subject": "GitHub password reset",
            "sender": "security@github.com",
            "body": (
                "A password reset was requested for your "
                "GitHub account."
            ),
            "timestamp": "2026-08-20T15:30:00",
        },
    ]

    pipeline = DiscoveryPipeline(
        email_provider=EmailProvider(emails),
        parser=EmailParser(),
    )

    results = pipeline.run()

    github_accounts = [
        result
        for result in results
        if result.service_name == "GitHub"
    ]

    assert len(github_accounts) == 1


def test_pipeline_aggregates_activity_dates() -> None:
    emails = [
        {
            "subject": "Welcome to GitHub",
            "sender": "noreply@github.com",
            "body": "Your GitHub account has been created.",
            "timestamp": "2026-01-10T10:00:00",
        },
        {
            "subject": "GitHub password reset",
            "sender": "security@github.com",
            "body": "A password reset was requested.",
            "timestamp": "2026-08-20T15:30:00",
        },
    ]

    pipeline = DiscoveryPipeline(
        email_provider=EmailProvider(emails),
    )

    results = pipeline.run()

    github = next(
        result
        for result in results
        if result.service_name == "GitHub"
    )

    assert github.first_seen == datetime(
        2026,
        1,
        10,
        10,
        0,
    )

    assert github.last_activity == datetime(
        2026,
        8,
        20,
        15,
        30,
    )


def test_pipeline_aggregates_evidence() -> None:
    from ..models.schemas import (
        AccountStatus,
        DataCategory,
        DiscoveredAccount,
        DiscoverySource,
    )
    from ..resolver.account_aggregator import AccountAggregator

    accounts = [
        DiscoveredAccount(
            service_name="GitHub",
            domain="github.com",
            relationship="development",
            source=DiscoverySource.EMAIL,
            first_seen=datetime(2026, 1, 10, 10, 0),
            last_activity=datetime(2026, 1, 10, 10, 0),
            data_categories=[],
            account_status=AccountStatus.UNKNOWN,
            evidence=["Welcome to GitHub"],
        ),
        DiscoveredAccount(
            service_name="GitHub",
            domain="github.com",
            relationship="development",
            source=DiscoverySource.EMAIL,
            first_seen=datetime(2026, 8, 20, 15, 30),
            last_activity=datetime(2026, 8, 20, 15, 30),
            data_categories=[],
            account_status=AccountStatus.UNKNOWN,
            evidence=["GitHub password reset"],
        ),
    ]

    aggregator = AccountAggregator()

    results = aggregator.aggregate(accounts)

    assert len(results) == 1

    github = results[0]

    assert "Welcome to GitHub" in github.evidence
    assert "GitHub password reset" in github.evidence
    assert len(github.evidence) == 2