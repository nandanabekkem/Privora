
def analyze_policy(policy_facts: dict) -> dict:
    """Summarize supplied privacy-policy facts using clear rules."""

    findings = []

    data_sharing = policy_facts.get("shares_data")
    deletion_available = policy_facts.get("deletion_available")
    retention_period = policy_facts.get("retention_period")

    if data_sharing is True:
        findings.append(
            "The supplied facts indicate that data is shared "
            "with third parties. Review who receives it."
        )
    elif data_sharing is False:
        findings.append(
            "The supplied facts indicate that data is not shared "
            "with third parties."
        )
    else:
        findings.append(
            "Data-sharing practices are unknown from the "
            "information provided."
        )

    if deletion_available is True:
        findings.append(
            "A deletion option is reported as available."
        )
    elif deletion_available is False:
        findings.append(
            "A deletion option is reported as unavailable. "
            "Check the service's official policy."
        )
    else:
        findings.append(
            "Deletion availability has not been established."
        )

    if retention_period:
        findings.append(
            f"Reported data-retention period: {retention_period}."
        )
    else:
        findings.append(
            "The data-retention period was not provided."
        )

    return {
        "findings": findings,
        "needs_review": (
            data_sharing is None
            or deletion_available is None
            or not retention_period
        ),
    }
