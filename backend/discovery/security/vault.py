from typing import Any, Dict, Optional


class IdentityVault:
    """
    Stores sensitive identity information separately from the
    sanitized context used by downstream AI components.

    This is an in-memory implementation for the MVP.
    Persistent encrypted storage can be added later.
    """

    def __init__(self) -> None:
        self._records: Dict[str, Dict[str, Any]] = {}

    def store(
        self,
        record_id: str,
        identity_data: Dict[str, Any],
    ) -> None:
        """
        Store sensitive identity information under a unique record ID.
        """
        self._records[record_id] = identity_data.copy()

    def get(
        self,
        record_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve stored identity information.
        """
        record = self._records.get(record_id)

        if record is None:
            return None

        return record.copy()

    def delete(
        self,
        record_id: str,
    ) -> bool:
        """
        Delete stored identity information.

        Returns True if a record was deleted.
        """
        if record_id not in self._records:
            return False

        del self._records[record_id]
        return True

    def exists(
        self,
        record_id: str,
    ) -> bool:
        """
        Check whether identity information exists for a record.
        """
        return record_id in self._records