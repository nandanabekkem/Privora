
def classify_personal_data(data_categories: list[str]) -> dict:
    """Classify the sensitivity of declared data categories."""

    sensitive_categories = {
        "financial",
        "health",
        "government_id",
        "biometric",
    }

    categories = [
        category.strip().lower()
        for category in data_categories
    ]

    found_sensitive = [
        category
        for category in categories
        if category in sensitive_categories
    ]

    if found_sensitive:
        sensitivity = "high"
    elif categories:
        sensitivity = "moderate"
    else:
        sensitivity = "unknown"

    return {
        "data_categories": categories,
        "sensitive_categories": found_sensitive,
        "sensitivity": sensitivity,
    }
