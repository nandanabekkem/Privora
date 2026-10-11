from datetime import datetime
from typing import Dict, List

from ..models.schemas import DiscoveredAccount


class AccountAggregator:
    """
    Merges multiple discovery records belonging to the same service.

    Example:

        GitHub email #1
        GitHub password reset
        GitHub notification
                ↓
            One GitHub account
    """

    def aggregate(
        self,
        accounts: List[DiscoveredAccount],
    ) -> List[DiscoveredAccount]:
        """
        Group discovered accounts by domain and merge their metadata.
        """
        grouped: Dict[str, DiscoveredAccount] = {}

        for account in accounts:
            existing = grouped.get(account.domain)

            if existing is None:
                grouped[account.domain] = account
                continue

            grouped[account.domain] = self._merge(
                existing,
                account,
            )

        return list(grouped.values())

    def _merge(
        self,
        existing: DiscoveredAccount,
        incoming: DiscoveredAccount,
    ) -> DiscoveredAccount:
        """
        Merge two records representing the same service.
        """
        first_seen = self._earliest_date(
            existing.first_seen,
            incoming.first_seen,
        )

        last_activity = self._latest_date(
            existing.last_activity,
            incoming.last_activity,
        )

        data_categories = list(
            dict.fromkeys(
                existing.data_categories
                + incoming.data_categories
            )
        )

        evidence = list(
            dict.fromkeys(
                existing.evidence
                + incoming.evidence
            )
        )

        relationship = (
            existing.relationship
            or incoming.relationship
        )

        return existing.model_copy(
            update={
                "relationship": relationship,
                "first_seen": first_seen,
                "last_activity": last_activity,
                "data_categories": data_categories,
                "evidence": evidence,
            }
        )

    def _earliest_date(
        self,
        first: datetime | None,
        second: datetime | None,
    ) -> datetime | None:
        """
        Return the earliest available timestamp.
        """
        if first is None:
            return second

        if second is None:
            return first

        return min(first, second)

    def _latest_date(
        self,
        first: datetime | None,
        second: datetime | None,
    ) -> datetime | None:
        """
        Return the latest available timestamp.
        """
        if first is None:
            return second

        if second is None:
            return first

        return max(first, second)