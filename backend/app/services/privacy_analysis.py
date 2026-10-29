"""Local account analysis and mock responses for the existing AI workflows."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Any

PII_PATTERNS = (
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"(?<!\d)\+?\d[\d\s().-]{7,}\d(?!\d)"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(?:\d{1,2}[/-]){2}\d{2,4}\b|\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b"),
)
MAX_CONTEXT_FIELD_LENGTH = 500
MAX_CATEGORY_LABEL_LENGTH = 64
MAX_CONTEXT_CATEGORIES = 100
KNOWN_DATA_CATEGORIES = {
    "contact", "email", "financial", "health", "government_id", "biometric",
    "location", "activity", "device", "identity", "preferences",
    "communications", "usage", "account", "other", "professional",
    "academic", "professional profile",
}


def sanitize_for_local_output(value: str) -> str:
    """Apply limited pattern-based cleanup before returning text in mock output."""
    cleaned = unicodedata.normalize("NFKC", str(value))[:2000]
    cleaned = " ".join(cleaned.split())
    for pattern, replacement in zip(PII_PATTERNS, ("[EMAIL]", "[PHONE]", "[ID]", "[DATE]")):
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned


def _context_string(value: Any, default: str = "") -> str:
    """Bound and pattern-sanitize account text used in local mock output."""
    return sanitize_for_local_output(str(value if value is not None else default))[:MAX_CONTEXT_FIELD_LENGTH]


def _context_timestamp(value: Any, default: str = "not recorded") -> str:
    """Preserve validated activity timestamps while sanitizing arbitrary values."""
    candidate = unicodedata.normalize("NFKC", str(value if value is not None else default)).strip()
    timestamp_pattern = re.compile(
        r"^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?$"
    )
    if timestamp_pattern.fullmatch(candidate):
        try:
            datetime.fromisoformat(candidate.replace("Z", "+00:00"))
            return candidate[:MAX_CONTEXT_FIELD_LENGTH]
        except ValueError:
            pass
    return _context_string(candidate, default)


def _normalize_category(value: Any) -> str | None:
    """Keep known labels canonical; do not pass unknown labels as model instructions."""
    normalized = unicodedata.normalize("NFKC", str(value)).strip().lower()
    if any(pattern.search(normalized) for pattern in PII_PATTERNS):
        return None
    normalized = sanitize_for_local_output(normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    # Category labels are identifiers, not prose. Restrict their alphabet,
    # length, and vocabulary so unexpected values cannot become prompt text.
    normalized = re.sub(r"[^a-z0-9 _-]", "", normalized)[:MAX_CATEGORY_LABEL_LENGTH].strip()
    if normalized in KNOWN_DATA_CATEGORIES:
        return normalized
    return None


def _bounded_categories(values: set[str]) -> tuple[list[str], int]:
    normalized = sorted({label for value in values if (label := _normalize_category(value))})
    omitted = len(values) - len(normalized)
    return normalized[:MAX_CONTEXT_CATEGORIES], omitted + max(0, len(normalized) - MAX_CONTEXT_CATEGORIES)


def analyze_stored_data(records: list[dict[str, Any]]) -> dict[str, Any]:
    categories = sorted(
        {
            str(record.get("category", "other")).strip().lower()
            for record in records
            if str(record.get("category", "")).strip()
        }
    )
    descriptions = " ".join(
        str(record.get("description", "")).lower()[:1000]
        for record in records
    )
    sensitive_terms = {
        "financial": ("financial", "bank", "payment", "card", "income"),
        "health": ("health", "medical", "diagnosis", "prescription"),
        "government_id": ("passport", "government id", "tax id", "ssn"),
        "biometric": ("biometric", "fingerprint", "face scan"),
    }
    detected = sorted(
        category
        for category, terms in sensitive_terms.items()
        if category in categories or any(term in descriptions for term in terms)
    )
    sensitivity = "high" if detected else "moderate" if records else "unknown"
    return {
        "categories": categories,
        "sensitive_categories": detected,
        "sensitivity": sensitivity,
        "record_count": len(records),
        "method": "category-and-description heuristic",
        "limitations": "This flags recorded descriptions only; it does not inspect provider systems or prove what a service holds.",
    }


def _account_context(account: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    analysis = analyze_stored_data(records)
    stored_categories, omitted_stored = _bounded_categories({
        str(record.get("category") or "")
        for record in records
        if record.get("category") and record.get("source") != "gmail_header_inference"
    })
    inferred_categories, omitted_inferred = _bounded_categories({
        str(record.get("category") or "")
        for record in records
        if record.get("category") and record.get("source") == "gmail_header_inference"
    })
    discovery_source = _context_string(account.get("discovery_source"), "unknown")
    evidence_note = (
        "Inferred from Gmail metadata; raw headers are excluded and this does not prove account ownership or activity."
        if discovery_source == "gmail"
        else _context_string(account.get("evidence_note"), "No evidence details are recorded.")
    )
    # Mock responses use only bounded account summaries; never echo record descriptions.
    return {
        "service": _context_string(account.get("service_name") or account.get("name"), "Unknown service"),
        "domain": _context_string(account.get("domain")),
        "website": _context_string(account.get("website")),
        "catalog_purpose": _context_string(account.get("purpose"), "Not documented"),
        "catalog_purpose_source": _context_string(account.get("purpose_source_url"), "No authoritative source recorded"),
        "data_categories": sorted(set(stored_categories + inferred_categories)),
        "stored_categories": stored_categories,
        "omitted_stored_category_count": omitted_stored,
        "sensitive_categories": analysis["sensitive_categories"],
        "sensitivity": analysis["sensitivity"],
        # Provenance is useful context, but raw email headers and record
        # descriptions are excluded from generated output.
        "discovery_source": discovery_source,
        "evidence_confidence": _context_string(account.get("evidence_confidence"), "unknown"),
        "last_evidence_at": _context_timestamp(account.get("last_evidence_at")),
        "evidence_note": evidence_note,
        "last_recorded_activity": _context_timestamp(account.get("last_activity")),
        "inferred_categories": inferred_categories,
        "omitted_inferred_category_count": omitted_inferred,
        "local_recommendation": _context_string(account.get("local_recommendation"))
        if account.get("local_recommendation")
        else "",
        "local_recommendation_reason": _context_string(account.get("local_recommendation_reason"))
        if account.get("local_recommendation_reason")
        else "",
    }


def _concise_analysis(context: dict[str, Any]) -> str:
    """Build a short, account-specific Privacy Analysis summary."""
    service = context["service"]
    purpose = context.get("catalog_purpose")
    if purpose and purpose != "Not documented":
        service_line = f"{service} is described in Privora's catalog as {purpose}."
    else:
        service_line = f"Privora has no service-purpose description recorded for {service}."

    sensitive = context.get("sensitive_categories", [])
    sensitivity = context.get("sensitivity", "unknown")
    if sensitive:
        stored = set(context.get("stored_categories", []))
        inferred = set(context.get("inferred_categories", []))
        sensitive_sources = []
        for category in sensitive:
            origins = [
                label
                for present, label in (
                    (category in stored, "recorded"),
                    (category in inferred, "inferred"),
                )
                if present
            ]
            source_label = f" ({' and '.join(origins)})" if origins else " (from stored descriptions)"
            sensitive_sources.append(f"{category}{source_label}")
        sensitivity_line = (
            f"The local sensitivity check rates this {sensitivity} because it flags "
            f"{', '.join(sensitive_sources)}."
        )
    elif sensitivity == "unknown":
        sensitivity_line = "Sensitivity is unknown because no data records are available."
    else:
        sensitivity_line = (
            f"Sensitivity is {sensitivity} because records exist, but no checked high-sensitivity "
            "category was flagged."
        )

    recorded = ", ".join(context.get("stored_categories", [])) or "none recorded"
    inferred = ", ".join(context.get("inferred_categories", [])) or "none"
    category_line = f"Recorded categories: {recorded}; inferred categories: {inferred}."
    privacy_line = (
        "Privacy consideration: these records do not verify what the provider currently holds."
    )
    return " ".join((service_line, sensitivity_line, category_line, privacy_line))


def _rules_answer(context: dict[str, Any], prompt: str, *, response_style: str = "conversation") -> str:
    if response_style == "privacy_analysis":
        return _concise_analysis(context)

    categories = ", ".join(context.get("stored_categories", context["data_categories"])) or "none recorded"
    sensitivities = ", ".join(context["sensitive_categories"]) or "none specifically flagged"
    omitted = context.get("omitted_stored_category_count", 0) + context.get("omitted_inferred_category_count", 0)
    omitted_note = f" {omitted} unrecognized or additional category labels were excluded from the local summary." if omitted else ""
    question_lower = prompt.lower()
    evidence = context.get("evidence_note", "No evidence details are recorded.")
    source = context.get("discovery_source", "unknown")
    if source == "gmail":
        provenance = f"Inventory evidence is inferred from Gmail metadata with {context.get('evidence_confidence', 'unknown')} confidence; {evidence} This does not prove account ownership or current activity."
    elif source == "synthetic":
        provenance = "This account is a synthetic sample, not a real discovery."
    else:
        provenance = f"Evidence source: {source}; {evidence}"
    purpose = context.get("catalog_purpose", "Not documented")
    purpose_line = (
        f"Catalog purpose: {purpose} (source: {context.get('catalog_purpose_source', 'not recorded')})."
        if purpose and purpose != "Not documented"
        else "No service purpose is documented for this account."
    )
    if any(word in question_lower for word in ("delete", "remove", "deletion")):
        summary = f"For {context['service']}, you can prepare an account-specific deletion-request draft. The available chat context does not establish a verified deletion channel. Draft creation does not send it; explicit approval and sending are separate steps."
    else:
        details = []
        if any(word in question_lower for word in ("purpose", "what does", "what is this service")):
            details.append(f"For {context['service']} ({context['domain'] or 'domain not recorded'}): {purpose_line}")
        if any(word in question_lower for word in ("recommend", "review", "retain", "keep this account", "forgotten account")):
            decision = context.get("local_recommendation")
            reason = context.get("local_recommendation_reason")
            if decision:
                inferred = ", ".join(context.get("inferred_categories", [])) or "none identified"
                details.append(
                    f"The existing local rules recommend {decision} for {context['service']}: {reason} "
                    f"Account context: stored categories {categories}; Gmail-inferred categories {inferred}; "
                    f"sensitivity {context['sensitivity']} (flags: {sensitivities}); "
                    f"recorded activity {context.get('last_recorded_activity', 'not recorded')}. {provenance}"
                )
            else:
                details.append(f"The selected account is {context['service']}; its stored activity and recorded categories are used by Privora's separate local recommendation rules.")
        if any(word in question_lower for word in ("activity", "active", "dormant", "last used", "last active")):
            activity = context.get("last_recorded_activity", "not recorded")
            activity_summary = (
                f"The selected {context['service']} account has a recorded activity date of {activity}."
                if activity != "not recorded"
                else f"No verified activity date is recorded for the selected {context['service']} account."
            )
            if source == "gmail":
                activity_summary += " Gmail header evidence is not proof of account activity."
            details.append(activity_summary)
        if any(word in question_lower for word in ("sensitive", "sensitivity", "data", "share", "information", "privacy", "concern", "risk", "personal")):
            inferred = ", ".join(context.get("inferred_categories", [])) or "none identified"
            details.append(
                f"Categories recorded in Privora for {context['service']}: {categories}. "
                f"Categories inferred from Gmail headers: {inferred}. The local sensitivity heuristic rates this "
                f"{context['sensitivity']} and flags: {sensitivities}. These records do not confirm what the provider currently holds. {provenance}"
            )
        if any(word in question_lower for word in ("discover", "found", "gmail", "verified", "own", "ownership", "real account", "prove")):
            details.append(
                f"Selected inventory account: {context['service']} ({context['domain'] or 'domain not recorded'}). "
                f"Discovery evidence: {provenance} It does not independently verify account ownership."
            )
        if not details:
            details.append(
                f"For the selected {context['service']} account, stored categories are {categories}; "
                f"Gmail-inferred categories are {', '.join(context.get('inferred_categories', [])) or 'none identified'}; "
                f"local sensitivity is {context['sensitivity']} (flags: {sensitivities}); "
                f"recorded activity is {context.get('last_recorded_activity', 'not recorded')}. "
                f"{purpose_line} {provenance}"
            )
        summary = " ".join(details)
    return f"{summary}{omitted_note} This is a mock/local response generated from this account's stored context and local rules; no AI provider was called, and this is not a provider audit."


def generate_account_answer(
    account: dict[str, Any],
    records: list[dict[str, Any]],
    question: str,
    history: list[dict[str, str]] | None = None,
    *,
    response_style: str = "conversation",
) -> dict[str, str]:
    context = _account_context(account, records)
    # Keep the existing history parameter for caller compatibility. Local
    # responses are derived from the current account context, not chat inference.
    prompt = sanitize_for_local_output(question)
    return {
        "mode": "mock_local",
        "answer": _rules_answer(context, prompt, response_style=response_style),
    }
