
from typing import Any


def classify_account(account: dict[str, Any]) -> dict[str, str]:
    """Classify an account using its service type and inactivity."""

    service_type = account.get("service_type", "unknown").lower()
    inactive_months = account.get("inactive_months", 0)

    if service_type in ("banking", "healthcare", "government"):
        risk_level = "high"
    elif inactive_months >= 12:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "account_name": account.get("name", "Unknown"),
        "service_type": service_type,
        "risk_level": risk_level,
    }
