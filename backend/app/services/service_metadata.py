"""Small, source-backed metadata for services already in Privora's catalog.

These are user-directed official guides, not provider deletion APIs. Review
source pages periodically; the metadata is not fetched or verified live.
"""

from urllib.parse import urlparse
from email.utils import parseaddr


CURATED_SERVICES = {
    "github.com": {
        "name": "GitHub",
        "purpose": "Code hosting with repository planning and collaboration tools.",
        "purpose_source_url": "https://docs.github.com/en/get-started/start-your-journey/what-is-github",
        "deletion_channel_url": "https://docs.github.com/en/account-and-profile/how-tos/account-management/deleting-your-personal-account",
        "deletion_channel_source_url": "https://docs.github.com/en/account-and-profile/how-tos/account-management/deleting-your-personal-account",
        "deletion_channel_type": "official_self_service_guide",
    },
    "linkedin.com": {
        "name": "LinkedIn",
        "purpose": "Professional networking for jobs, connections, and career opportunities.",
        "purpose_source_url": "https://www.linkedin.com/help/linkedin/answer/a548441/what-is-linkedin-and-how-can-i-use-it",
        "deletion_channel_url": "https://www.linkedin.com/help/linkedin/answer/a1379064",
        "deletion_channel_source_url": "https://www.linkedin.com/help/linkedin/answer/a1379064",
        "deletion_channel_type": "official_self_service_guide",
    },
}


def _normalize_host(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else f"https://{value}")
    return (parsed.hostname or "").lower().removeprefix("www.").rstrip(".")


def metadata_for_service(
    *,
    name: str | None = None,
    domain: str | None = None,
    website: str | None = None,
) -> dict | None:
    """Return curated data only for exact domains or a matching catalog site."""
    host = _normalize_host(domain) or _normalize_host(website)
    if host:
        for canonical_domain, metadata in CURATED_SERVICES.items():
            if host == canonical_domain or host.endswith(f".{canonical_domain}"):
                return dict(metadata)
        return None

    normalized_name = (name or "").strip().casefold()
    for metadata in CURATED_SERVICES.values():
        if normalized_name == metadata["name"].casefold():
            return dict(metadata)
    return None


def verified_deletion_email(service: dict, website: str | None) -> tuple[str, str] | None:
    """Accept only an email and evidence URL on the service's own HTTPS domain."""
    recipient = str(service.get("deletion_email") or "").strip()
    source_url = str(service.get("deletion_email_source_url") or "").strip()
    parsed_source = urlparse(source_url)
    _, parsed_recipient = parseaddr(recipient)
    if parsed_recipient != recipient or recipient.count("@") != 1:
        return None
    recipient_host = recipient.rsplit("@", 1)[1].lower().rstrip(".")
    website_host = _normalize_host(website)
    source_host = _normalize_host(source_url)
    if not (
        parsed_source.scheme == "https"
        and website_host
        and source_host
        and (source_host == website_host or source_host.endswith(f".{website_host}"))
        and (recipient_host == website_host or recipient_host.endswith(f".{website_host}"))
    ):
        return None
    return recipient, source_url
