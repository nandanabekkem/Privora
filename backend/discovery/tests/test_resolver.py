import pytest

from ..resolver.service_resolver import ServiceResolver


@pytest.fixture
def resolver() -> ServiceResolver:
    return ServiceResolver()


@pytest.mark.parametrize(
    ("domain", "service_name", "relationship"),
    [
        ("github.com", "GitHub", "development"),
        ("linkedin.com", "LinkedIn", "professional"),
        ("coursera.org", "Coursera", "education"),
        ("udemy.com", "Udemy", "education"),
        ("internshala.com", "Internshala", "internship"),
        ("unstop.com", "Unstop", "hackathon"),
        ("devpost.com", "Devpost", "hackathon"),
        ("amazon.in", "Amazon", "shopping"),
        ("flipkart.com", "Flipkart", "shopping"),
        ("swiggy.com", "Swiggy", "shopping"),
        ("zomato.com", "Zomato", "shopping"),
    ],
)
def test_resolve_known_services(
    resolver: ServiceResolver,
    domain: str,
    service_name: str,
    relationship: str,
) -> None:
    result = resolver.resolve(domain)

    assert result["service_name"] == service_name
    assert result["domain"] == domain
    assert result["relationship"] == relationship


def test_resolve_known_service_with_www(
    resolver: ServiceResolver,
) -> None:
    result = resolver.resolve("www.linkedin.com")

    assert result["service_name"] == "LinkedIn"
    assert result["domain"] == "linkedin.com"
    assert result["relationship"] == "professional"


def test_resolve_domain_case_insensitively(
    resolver: ServiceResolver,
) -> None:
    result = resolver.resolve("COURSERA.ORG")

    assert result["service_name"] == "Coursera"
    assert result["domain"] == "coursera.org"
    assert result["relationship"] == "education"


def test_resolve_unknown_service(
    resolver: ServiceResolver,
) -> None:
    result = resolver.resolve("unknown-platform.com")

    assert result["service_name"] == "Unknown Platform"
    assert result["domain"] == "unknown-platform.com"
    assert result["relationship"] is None


def test_resolve_hyphenated_domain(
    resolver: ServiceResolver,
) -> None:
    result = resolver.resolve("my-learning-platform.com")

    assert result["service_name"] == "My Learning Platform"
    assert result["domain"] == "my-learning-platform.com"


def test_resolve_underscored_domain(
    resolver: ServiceResolver,
) -> None:
    result = resolver.resolve("my_learning_platform.com")

    assert result["service_name"] == "My Learning Platform"
    assert result["domain"] == "my_learning_platform.com"


def test_resolve_empty_domain(
    resolver: ServiceResolver,
) -> None:
    result = resolver.resolve("")

    assert result["service_name"] == "Unknown Service"
    assert result["domain"] == ""
    assert result["relationship"] is None