import re
from datetime import datetime, timedelta, timezone


DEFAULT_DAYS_THRESHOLD = 90
MIN_DAYS_THRESHOLD = 1
MAX_DAYS_THRESHOLD = 3650


def evaluate_account(
    account,
    days_threshold: int = DEFAULT_DAYS_THRESHOLD,
    policies=None,
) -> dict:
    """
    Evaluate an account using activity, mapped data, and user policies.

    This function only makes recommendations.
    It never modifies or deletes accounts.

    Safety rules:
    - User approval is required by default.
    - Only supported inactivity policies change the threshold.
    - Policies never trigger automatic account deletion.
    """

    if not isinstance(days_threshold, int) or isinstance(days_threshold, bool):
        raise ValueError("days_threshold must be an integer")

    if not MIN_DAYS_THRESHOLD <= days_threshold <= MAX_DAYS_THRESHOLD:
        raise ValueError(
            f"days_threshold must be between "
            f"{MIN_DAYS_THRESHOLD} and {MAX_DAYS_THRESHOLD}"
        )

    policies = list(policies or [])

    last_activity = account.last_activity
    data_records = account.data_records or []

    # Normalize saved policy text.
    policy_texts = []

    for policy in policies:
        policy_type = str(getattr(policy, "policy_type", "") or "")
        policy_text = str(getattr(policy, "policy_text", "") or "")

        combined_text = f"{policy_type} {policy_text}".strip().lower()

        if combined_text:
            policy_texts.append(combined_text)

    # Apply explicitly stated inactivity thresholds.
    # Example: "Review accounts inactive for more than 120 days."
    for text in policy_texts:
        if "inactive" not in text and "inactivity" not in text:
            continue

        match = re.search(
            r"\b(\d+)\s*days?\b",
            text,
        )

        if match:
            requested_days = int(match.group(1))

            if MIN_DAYS_THRESHOLD <= requested_days <= MAX_DAYS_THRESHOLD:
                days_threshold = requested_days
                break

    # Require approval by default.
    # A saved policy never disables approval through keyword matching.
    approval_required = True

    # Handle missing activity information safely.
    if last_activity is None:
        return {
            "account_id": account.id,
            "service": account.service.name,
            "recommendation": "REVIEW",
            "reason": (
                "No last-activity date is recorded. "
                "Check the account's activity before deciding what to do."
            ),
            "days_threshold": days_threshold,
            "applied_policy_count": len(policies),
            "requires_user_approval": approval_required,
        }

    # Treat timezone-naive timestamps as UTC.
    if last_activity.tzinfo is None:
        last_activity = last_activity.replace(tzinfo=timezone.utc)

    cutoff_date = datetime.now(timezone.utc) - timedelta(
        days=days_threshold
    )

    if last_activity <= cutoff_date:
        recommendation = "REVIEW"
        reason = (
            f"No activity recorded in at least {days_threshold} days. "
            "Review whether this account is still needed."
        )

    elif data_records:
        recommendation = "KEEP"
        reason = (
            "Recent activity is recorded and data categories are mapped. "
            "Keep the account unless the user decides otherwise."
        )

    else:
        recommendation = "REVIEW"
        reason = (
            "Recent activity is recorded, but no data categories are mapped. "
            "Review the account's data map."
        )

    if policies:
        reason += (
            f" Evaluated with {len(policies)} saved user policy/policies."
        )

    return {
        "account_id": account.id,
        "service": account.service.name,
        "recommendation": recommendation,
        "reason": reason,
        "days_threshold": days_threshold,
        "applied_policy_count": len(policies),
        "requires_user_approval": approval_required,
    }