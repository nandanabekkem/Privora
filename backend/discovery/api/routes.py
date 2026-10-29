from __future__ import annotations

import hashlib
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from google.auth.exceptions import TransportError
from googleapiclient.errors import HttpError
from requests import RequestException

if __package__.startswith("backend."):
    from ...app.core.authentication import (
        authorize_user_path,
        canonical_user_id,
        get_current_user,
    )
else:
    from app.core.authentication import (
        authorize_user_path,
        canonical_user_id,
        get_current_user,
    )
from ..core.config import config
from ..pipeline.discovery_pipeline import DiscoveryPipeline
from ..security.gmail_oauth import (
    GmailOAuthConfigurationError,
    _consume_state,
    begin_gmail_authorization,
    complete_gmail_authorization,
    gmail_credentials,
    save_refreshed_credentials,
)
from ..sources.email.gmail_provider import GmailAuthorizationError
from ..sources.email.provider import EmailProvider

if __package__.startswith("backend."):
    from ...app.core.firestore_store import (
        collection,
        get_document,
        list_documents,
        list_by_field,
    )
else:
    from app.core.firestore_store import (
        collection,
        get_document,
        list_documents,
        list_by_field,
    )

router = APIRouter(
    prefix="/discovery",
    tags=["discovery"],
)


def _get_synthetic_pipeline() -> DiscoveryPipeline:
    return DiscoveryPipeline(
        email_provider=EmailProvider.synthetic(),
    )


def _get_gmail_pipeline(uid: str) -> DiscoveryPipeline:
    credentials = gmail_credentials(uid)
    return DiscoveryPipeline.from_gmail(
        max_results=config.max_emails,
        credentials=credentials,
        save_credentials=lambda updated: save_refreshed_credentials(
            uid, updated
        ),
    )


def _persist_gmail_candidates(user_id: int | str, candidates: list[dict]) -> None:
    """Persist header-derived candidates without asserting account activity."""
    services = list_documents("services")
    for candidate in candidates:
        domain = str(candidate.get("domain") or "").strip().lower()
        if not domain:
            continue

        service_name = candidate.get("service_name") or domain
        service = next(
            (
                item for item in services
                if str(item.get("name", "")).casefold() == str(service_name).casefold()
            ),
            {},
        )
        account_id = hashlib.sha256(f"{user_id}:{domain}".encode()).hexdigest()
        account_data = {
            "user_id": user_id,
            "domain": domain,
            "service_name": service_name,
            "service_id": service.get("id"),
            # A sender domain is not proof of an official service website.
            "website": service.get("website"),
            "purpose": service.get("purpose"),
            "status": "UNKNOWN",
            "discovery_source": "gmail",
            "last_evidence_at": candidate.get("last_activity"),
            # A received email is evidence of correspondence, not verified
            # service activity. Never use it as the dormancy activity date.
        }
        account_ref = collection("accounts").document(account_id)
        existing = get_document("accounts", account_id)
        if existing and str(existing.get("user_id")) != str(user_id):
            continue
        if existing:
            account_ref.update(account_data)
        else:
            account_ref.set(account_data)

        existing_categories = {
            str(record.get("category", "")).casefold()
            for record in list_by_field("data_records", "account_id", account_id)
        }
        for category in candidate.get("data_categories", []):
            category_value = str(category).split(".")[-1].lower()
            if not category_value or category_value.casefold() in existing_categories:
                continue
            record_id = hashlib.sha256(
                f"{account_id}:{category_value}".encode()
            ).hexdigest()
            collection("data_records").document(record_id).set(
                {
                    "account_id": account_id,
                    "category": category_value,
                    "description": (
                        "Potential category inferred from Gmail message headers; "
                        "verify with the service."
                    ),
                    "source": "gmail_header_inference",
                }
            )


@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "discovery",
    }


@router.post("/gmail/authorize")
def authorize_gmail(current_user: dict = Depends(get_current_user)):
    try:
        authorization_url = begin_gmail_authorization(current_user["uid"])
    except GmailOAuthConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"authorization_url": authorization_url}


@router.get("/gmail/status")
def gmail_status(current_user: dict = Depends(get_current_user)) -> dict[str, object]:
    """Report whether this Firebase user's Gmail credentials are usable."""
    try:
        gmail_credentials(current_user["uid"])
    except LookupError:
        return {"status": "not_connected", "connected": False}
    except GmailAuthorizationError:
        return {"status": "reconnect_required", "connected": False}
    except GmailOAuthConfigurationError:
        return {"status": "configuration_error", "connected": False}
    except (TransportError, RequestException):
        return {"status": "temporarily_unavailable", "connected": False}
    return {"status": "authorization_ready", "connected": True}


@router.get("/gmail/callback")
def gmail_oauth_callback(
    state: str | None = None,
    code: str | None = None,
    error: str | None = None,
):
    if not state:
        raise HTTPException(status_code=400, detail="Missing OAuth state")
    if error:
        _consume_state(state)
        return RedirectResponse(
            f"{config.frontend_url.rstrip('/')}/?gmail=denied",
            status_code=303,
        )
    if not code:
        raise HTTPException(status_code=400, detail="Missing OAuth code")
    try:
        complete_gmail_authorization(code, state)
    except GmailOAuthConfigurationError:
        return RedirectResponse(
            f"{config.frontend_url.rstrip('/')}?{urlencode({'gmail': 'error', 'reason': 'configuration'})}",
            status_code=303,
        )
    except (ValueError, KeyError) as exc:
        message = str(exc).casefold()
        reason = (
            "expired" if "expired" in message else
            "offline_access" if "offline access" in message else
            "failed"
        )
        return RedirectResponse(
            f"{config.frontend_url.rstrip('/')}?{urlencode({'gmail': 'error', 'reason': reason})}",
            status_code=303,
        )
    return RedirectResponse(
        f"{config.frontend_url.rstrip('/')}/?gmail=connected",
        status_code=303,
    )


@router.post("/run")
def run_discovery(
    source: str = Query(
        default="synthetic",
        pattern="^(synthetic|gmail)$",
    ),
    current_user: dict = Depends(get_current_user),
) -> dict[str, object]:
    if source == "gmail":
        try:
            pipeline = _get_gmail_pipeline(current_user["uid"])
        except (LookupError, GmailAuthorizationError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except GmailOAuthConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except (TransportError, RequestException) as exc:
            raise HTTPException(
                status_code=503,
                detail="Gmail authorization could not be refreshed due to a network error. Reconnect Gmail and try again.",
            ) from exc
    else:
        pipeline = _get_synthetic_pipeline()

    try:
        results = pipeline.run()
    except GmailAuthorizationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except HttpError as exc:
        provider_status = getattr(getattr(exc, "resp", None), "status", None)
        if provider_status in {401, 403}:
            raise HTTPException(
                status_code=409,
                detail="Gmail rejected this authorization. Reconnect Gmail and verify Gmail API access.",
            ) from exc
        status_code = 503 if provider_status == 429 or (provider_status and provider_status >= 500) else 502
        raise HTTPException(
            status_code=status_code,
            detail="Gmail could not complete the metadata scan. Try again later.",
        ) from exc
    except (TransportError, RequestException) as exc:
        raise HTTPException(
            status_code=503,
            detail="Gmail could not be reached for the metadata scan. Check the connection and try again.",
        ) from exc
    serialized_results = [result.model_dump(mode="json") for result in results]
    if source == "gmail":
        owner = authorize_user_path(current_user["uid"], current_user)
        _persist_gmail_candidates(
            canonical_user_id(owner),
            serialized_results,
        )

    return {
        "status": "success",
        "source": source,
        "source_label": (
            "Synthetic sample data; not a real account discovery"
            if source == "synthetic"
            else "Gmail evidence; candidate accounts are not provider-verified"
        ),
        "count": len(results),
        "accounts": [
            result
            for result in serialized_results
        ],
    }
