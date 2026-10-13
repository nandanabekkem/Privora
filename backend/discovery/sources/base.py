from abc import ABC, abstractmethod
from typing import Any, List


class DiscoverySource(ABC):
    """
    Base interface for all account discovery sources.

    New sources such as Gmail, password managers, browser history,
    or account exports should implement this interface.
    """

    @abstractmethod
    def fetch_records(self) -> List[Any]:
        """
        Fetch raw records from the discovery source.
        """
        raise NotImplementedError