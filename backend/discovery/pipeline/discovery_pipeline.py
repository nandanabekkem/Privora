from datetime import datetime
from typing import Any, Dict, List
from ..sources.email.gmail_provider import GmailProvider
from ..core.constants import GMAIL_DISCOVERY_QUERY

from ..models.schemas import (
    AccountStatus,
    DataCategory,
    DiscoveredAccount,
    DiscoverySource,
    SanitizedAccountContext,
)
from ..resolver.account_aggregator import AccountAggregator
from ..resolver.service_resolver import ServiceResolver
from ..security.sanitizer import DataSanitizer
from ..security.vault import IdentityVault
from ..sources.email.parser import EmailParser
from ..sources.email.provider import EmailProvider


class DiscoveryPipeline:
    """
    Orchestrates the complete discovery flow:

    Discovery source
        ↓
    Parser
        ↓
    Service resolver
        ↓
    Identity vault
        ↓
    Account aggregation
        ↓
    Sanitization
        ↓
    Structured discovery context
    """

    def __init__(
        self,
        email_provider: EmailProvider,
        parser: EmailParser | None = None,
        resolver: ServiceResolver | None = None,
        sanitizer: DataSanitizer | None = None,
        vault: IdentityVault | None = None,
        aggregator: AccountAggregator | None = None,
    ) -> None:
        self.email_provider = email_provider
        self.parser = parser or EmailParser()
        self.resolver = resolver or ServiceResolver()
        self.sanitizer = sanitizer or DataSanitizer()
        self.vault = vault or IdentityVault()
        self.aggregator = aggregator or AccountAggregator()

    
    def run(self) -> List[SanitizedAccountContext]:
        """
        Run account discovery and return one sanitized context
        per discovered service.
        """
        discovery_fetcher = getattr(
            self.email_provider,
            "fetch_discovery_records",
            None,
        )

        if callable(discovery_fetcher):
            raw_emails = discovery_fetcher(
                query=GMAIL_DISCOVERY_QUERY,
            )
        else:
            # Synthetic and other providers retain their existing behavior.
            raw_emails = self.email_provider.fetch_records()

        parsed_emails = self.parser.parse_many(raw_emails)

        discovered_accounts: List[DiscoveredAccount] = []

        for email in parsed_emails:
            account = self._build_account(email)

            if account is not None:
                discovered_accounts.append(account)

        aggregated_accounts = self.aggregator.aggregate(
            discovered_accounts
        )

        return [
            self._create_sanitized_context(account)
            for account in aggregated_accounts
        ]

    def _build_account(
        self,
        parsed_email: Dict[str, Any],
    ) -> DiscoveredAccount | None:
        """
        Convert parsed email data into a structured account.
        """
        domain = parsed_email.get("domain")

        if not domain:
            return None

        service = self.resolver.resolve(domain)

        timestamp = parsed_email.get("timestamp")

        record_id = self._create_record_id(
            domain=service["domain"],
            timestamp=timestamp,
        )

        self._store_identity_data(
            record_id=record_id,
            parsed_email=parsed_email,
        )

        relationship = (
            parsed_email.get("relationship")
            or service.get("relationship")
        )

        data_categories = self._convert_data_categories(
            parsed_email.get("data_categories", [])
        )

        return DiscoveredAccount(
            service_name=service["service_name"] or "Unknown Service",
            domain=service["domain"],
            relationship=relationship,
            source=DiscoverySource.EMAIL,
            first_seen=timestamp,
            last_activity=timestamp,
            data_categories=data_categories,
            account_status=AccountStatus.UNKNOWN,
            evidence=[
                parsed_email.get("subject", ""),
            ],
        )

    def _store_identity_data(
        self,
        record_id: str,
        parsed_email: Dict[str, Any],
    ) -> None:
        """
        Store raw identity-bearing information separately from
        the sanitized discovery context.
        """
        identity_data = {
            "sender": parsed_email.get("sender"),
            "email_body": parsed_email.get("body"),
        }

        self.vault.store(
            record_id,
            identity_data,
        )

    def _create_sanitized_context(
        self,
        account: DiscoveredAccount,
    ) -> SanitizedAccountContext:
        """
        Create the minimal context that can safely move
        downstream to the AI/backend layer.
        """
        return SanitizedAccountContext(
            service_name=account.service_name,
            domain=account.domain,
            relationship=account.relationship,
            source=account.source,
            first_seen=account.first_seen,
            last_activity=account.last_activity,
            data_categories=account.data_categories,
            account_status=account.account_status,
        )

    def _convert_data_categories(
        self,
        categories: List[str],
    ) -> List[DataCategory]:
        """
        Convert parser-level category strings into the shared
        schema enum used across the discovery module.
        """
        valid_categories = {
            category.value
            for category in DataCategory
        }

        return [
            DataCategory(category)
            for category in categories
            if category in valid_categories
        ]

    def _create_record_id(
        self,
        domain: str,
        timestamp: datetime | None,
    ) -> str:
        """
        Create a stable identifier for a discovered email record.
        """
        timestamp_value = (
            timestamp.isoformat()
            if timestamp
            else "unknown"
        )

        return f"{domain}:{timestamp_value}"

    @classmethod
    def from_gmail(
    cls,
    credentials_path: str = "credentials.json",
    token_path: str = "token.json",
) -> "DiscoveryPipeline":
      email_provider = GmailProvider(
        credentials_path=credentials_path,
        token_path=token_path,
    )
      return cls(
        email_provider=email_provider,
    )