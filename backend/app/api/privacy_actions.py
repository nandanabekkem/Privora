
from datetime import datetime, timezone
from email.utils import parseaddr
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field, field_validator

from ..core.authentication import (
    authorize_user_path,
    canonical_user_id,
    get_current_user,
    validate_numeric_user_path,
)
from ..core import firestore_store
from ..core.firestore_store import (
    create_action_with_audit,
    create_document,
    collection,
    get_document,
    list_by_field,
    review_action_with_audit,
    transactional,
    update_document,
)
from googleapiclient.errors import HttpError

from ..services.service_metadata import metadata_for_service, verified_deletion_email
if __package__.startswith("backend."):
    from ...discovery.security.gmail_oauth import GmailOAuthConfigurationError, gmail_credentials, save_refreshed_credentials
    from ...discovery.sources.email.gmail_provider import GmailAuthorizationError, GmailProvider
else:
    from discovery.security.gmail_oauth import GmailOAuthConfigurationError, gmail_credentials, save_refreshed_credentials
    from discovery.sources.email.gmail_provider import GmailAuthorizationError, GmailProvider


router = APIRouter(
    prefix="/privacy-actions",
    tags=["Privacy Actions"],
)


class PrivacyActionCreate(BaseModel):
    account_id: int | str = Field()
    action_type: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=2000)

    @field_validator("action_type", "description")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError(
                "This field cannot be empty or contain only spaces"
            )
        return value

    @field_validator("account_id")
    @classmethod
    def validate_account_id(cls, value):
        if isinstance(value, int) and value <= 0:
            raise ValueError("Account ID must be positive")
        if isinstance(value, str) and not value.strip():
            raise ValueError("Account ID cannot be blank")
        return value


class PrivacyActionReview(BaseModel):
    decision: str = Field(min_length=1, max_length=20)

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"APPROVE", "REJECT"}:
            raise ValueError("Decision must be APPROVE or REJECT")
        return value


class RequestTrackingUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=30)
    reply_note: str | None = Field(default=None, max_length=1000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in {"SENT_BY_USER", "REPLY_RECEIVED"}:
            raise ValueError("Unsupported user-reported request status")
        return value


def numeric_id(value):
    return int(value) if str(value).isdigit() else value


def get_user_actions(user_id: int | str) -> list[dict]:
    actions = list_by_field("privacy_actions", "user_id", user_id)
    actions.extend(
        list_by_field("privacy_actions", "user_id", str(user_id))
    )

    unique = {action["id"]: action for action in actions}
    return sorted(
        unique.values(),
        key=lambda action: action.get("created_at") or 0,
        reverse=True,
    )


@router.post("/{user_id}", status_code=201)
def create_privacy_action(
    payload: PrivacyActionCreate,
    user_id: str = Path(min_length=1),
    claims: dict = Depends(get_current_user),
):
    validate_numeric_user_path(user_id)
    user = authorize_user_path(user_id, claims)
    owned_user_id = canonical_user_id(user)

    account = get_document("accounts", payload.account_id)
    if account is None or str(account.get("user_id")) != str(owned_user_id):
        raise HTTPException(
            status_code=404,
            detail="Account not found for this user",
        )

    action = create_action_with_audit(
        user_id=owned_user_id,
        account_id=payload.account_id,
        action_type=payload.action_type,
        description=payload.description,
    )

    return {
        "id": numeric_id(action["id"]),
        "user_id": action["user_id"],
        "account_id": action["account_id"],
        "action_type": action["action_type"],
        "description": action["description"],
        "status": action["status"],
        "requires_approval": action["requires_approval"],
        "created_at": action["created_at"],
        "message": "Proposed action created. User approval is required.",
    }


@router.get("/{user_id}")
def list_privacy_actions(
    user_id: str = Path(min_length=1),
    claims: dict = Depends(get_current_user),
):
    validate_numeric_user_path(user_id)
    user = authorize_user_path(user_id, claims)
    owned_user_id = canonical_user_id(user)

    actions = get_user_actions(owned_user_id)

    return {
        "user_id": owned_user_id,
        "count": len(actions),
        "actions": [
            {
                "id": numeric_id(action["id"]),
                "account_id": numeric_id(action["account_id"]),
                "action_type": action.get("action_type"),
                "description": action.get("description"),
                "status": action.get("status"),
                "requires_approval": action.get("requires_approval", True),
                "created_at": action.get("created_at"),
                "reviewed_at": action.get("reviewed_at"),
        "request_status": action.get("request_status"),
        "reply_status": action.get("reply_status"),
        "request_subject": action.get("request_subject"),
        "request_body": action.get("request_body"),
        "channel_url": action.get("channel_url"),
        "channel_catalogued": action.get("channel_catalogued", False),
        "channel_type": action.get("channel_type"),
        "channel_source_url": action.get("channel_source_url"),
        "channel_email": action.get("channel_email"),
        "reply_detection_source": action.get("reply_detection_source"),
        "reply_candidate_at": action.get("reply_candidate_at"),
            }
            for action in actions
        ],
    }


@router.post("/{user_id}/{action_id}/review")
def review_privacy_action(
    payload: PrivacyActionReview,
    user_id: str = Path(min_length=1),
    action_id: str = Path(min_length=1),
    claims: dict = Depends(get_current_user),
):
    validate_numeric_user_path(user_id)
    user = authorize_user_path(user_id, claims)
    owned_user_id = canonical_user_id(user)
    result = review_action_with_audit(
        user_id=owned_user_id,
        action_id=action_id,
        decision=payload.decision,
    )

    if result.get("error") == "not_found":
        raise HTTPException(
            status_code=404,
            detail="Privacy action not found",
        )

    if result.get("error") == "not_pending":
        raise HTTPException(
            status_code=409,
            detail="Only pending actions can be reviewed",
        )

    return {
        "id": numeric_id(result["id"]),
        "status": result["status"],
        "reviewed_at": result["reviewed_at"],
        "message": (
            "Approval recorded. No external account action was executed."
            if payload.decision == "APPROVE"
            else "Rejection recorded. No external account action was executed."
        ),
    }


@router.post("/{user_id}/accounts/{account_id}/deletion-draft", status_code=201)
def create_deletion_request_draft(
    user_id: str,
    account_id: str,
    claims: dict = Depends(get_current_user),
):
    validate_numeric_user_path(user_id)
    user = authorize_user_path(user_id, claims)
    owned_user_id = canonical_user_id(user)
    account = get_document("accounts", account_id)
    if account is None or str(account.get("user_id")) != str(owned_user_id):
        raise HTTPException(status_code=404, detail="Account not found for this user")

    service = get_document("services", account["service_id"]) if account.get("service_id") else None
    service_name = (service or {}).get("name", account.get("service_name", "the service"))
    source_metadata = metadata_for_service(
        name=service_name,
        domain=account.get("domain"),
        website=(service or {}).get("website") or account.get("website"),
    ) or {}
    channel_url = (
        source_metadata.get("deletion_channel_url")
        or (service or {}).get("deletion_request_url")
        or (service or {}).get("privacy_url")
    )
    channel_source_url = source_metadata.get("deletion_channel_source_url")
    channel_type = source_metadata.get("deletion_channel_type", "catalogued_request_channel")
    channel_email = None
    channel_catalogued = False
    if channel_url and channel_source_url:
        parsed_channel = urlparse(channel_url)
        parsed_source = urlparse(channel_source_url)
        channel_catalogued = bool(
            parsed_channel.scheme == "https"
            and parsed_channel.hostname == parsed_source.hostname
            and parsed_channel.hostname
        )
    elif channel_url and (service or {}).get("website"):
        channel_host = (urlparse(channel_url).hostname or "").lower().rstrip(".")
        website_host = (urlparse(service["website"]).hostname or "").lower().rstrip(".")
        channel_catalogued = bool(
            urlparse(channel_url).scheme == "https"
            and website_host
            and (channel_host == website_host or channel_host.endswith(f".{website_host}"))
        )
    if not channel_catalogued:
        email_channel = verified_deletion_email(
            service or {}, (service or {}).get("website") or account.get("website")
        )
        if email_channel:
            channel_email, channel_source_url = email_channel
            channel_type = "official_email"
            channel_catalogued = True
    if not channel_catalogued:
        channel_url = None
    body = (
        f"Hello {service_name} Privacy Team,\n\n"
        f"Regarding my account with {service_name}, I request deletion of that account and its personal data, "
        "subject to any retention required by applicable law. Please tell me if you need "
        "additional information to verify my identity and confirm the outcome. This request "
        "will be sent from my email address if I choose to submit it; if that does not identify the account, please reply "
        "with a secure verification method. Do not request my password or one-time codes."
    )
    action = create_action_with_audit(
        user_id=owned_user_id,
        account_id=account_id,
        action_type="DELETE_REQUEST_DRAFT",
        description=f"Deletion request draft for {service_name}",
        metadata={
            "request_status": "PENDING_APPROVAL",
            "reply_status": "NO_REPLY",
            "request_subject": f"Request to delete my {service_name} account and personal data",
            "request_body": body,
            "channel_url": channel_url,
            "channel_catalogued": channel_catalogued,
            "channel_type": channel_type if channel_catalogued else None,
            "channel_source_url": channel_source_url if channel_catalogued else None,
            "channel_email": channel_email if channel_type == "official_email" else None,
            "tracking_source": "user_reported",
            "sent_at": None,
            "reply_note": None,
        },
    )
    return {
        "id": action["id"],
        "account_id": account_id,
        "status": "PENDING",
        "request_status": "PENDING_APPROVAL",
        "subject": action["request_subject"],
        "body": body,
        "channel_url": channel_url,
        "channel_catalogued": channel_catalogued,
        "channel_type": channel_type if channel_catalogued else None,
        "channel_source_url": channel_source_url if channel_catalogued else None,
        "channel_email": channel_email if channel_type == "official_email" else None,
        "channel_notice": (
            "Official self-service guidance; Privora cannot submit the account closure for this service."
            if channel_type == "official_self_service_guide" and channel_catalogued
            else "The email address is source-verified on the service's HTTPS domain; sending requires a Gmail authorization and your separate approval."
            if channel_type == "official_email" and channel_catalogued
            else "Request channel supplied by the service catalog; verify it before use."
            if channel_catalogued
            else "No official request channel is catalogued."
        ),
        "message": "Draft saved for your review. Privora has not sent it.",
    }


@router.post("/{user_id}/{action_id}/send")
def send_approved_deletion_request(
    user_id: str,
    action_id: str = Path(min_length=1),
    claims: dict = Depends(get_current_user),
):
    """Send only an approved draft to its source-verified service email."""
    validate_numeric_user_path(user_id)
    user = authorize_user_path(user_id, claims)
    owned_user_id = canonical_user_id(user)
    action_ref = collection("privacy_actions").document(action_id)
    action = get_document("privacy_actions", action_id)
    if (
        action is None
        or str(action.get("user_id")) != str(owned_user_id)
        or action.get("action_type") != "DELETE_REQUEST_DRAFT"
    ):
        raise HTTPException(status_code=404, detail="Deletion request not found")
    if action.get("status") != "APPROVED" or action.get("request_status") != "APPROVED_NOT_SENT":
        raise HTTPException(status_code=409, detail="Approve this draft before sending it")
    if action.get("channel_type") != "official_email" or not action.get("channel_email"):
        raise HTTPException(status_code=409, detail="No source-verified email sending channel is available")
    if not action.get("request_subject") or not action.get("request_body"):
        raise HTTPException(status_code=409, detail="The deletion request draft is incomplete")

    account = get_document("accounts", action.get("account_id"))
    service = get_document("services", account["service_id"]) if account and account.get("service_id") else None
    website = (service or {}).get("website") or (account or {}).get("website")
    verified_email = verified_deletion_email(service or {}, website)
    if verified_email != (action.get("channel_email"), action.get("channel_source_url")):
        raise HTTPException(status_code=409, detail="The service email or its official source has changed; create a new draft")

    db = firestore_store.get_firestore_client()
    log_ref = collection("audit_logs").document()

    @transactional
    def claim_send(transaction):
        snapshot = action_ref.get(transaction=transaction)
        if not snapshot.exists:
            return "not_found"
        current = snapshot.to_dict() or {}
        if str(current.get("user_id")) != str(owned_user_id):
            return "not_found"
        if current.get("status") != "APPROVED" or current.get("request_status") != "APPROVED_NOT_SENT":
            return "not_pending"
        transaction.update(action_ref, {"request_status": "SENDING"})
        transaction.set(log_ref, {
            "user_id": owned_user_id,
            "privacy_action_id": action_id,
            "event_type": "REQUEST_SEND_STARTED",
            "details": "An explicitly approved deletion request was submitted to Gmail for sending.",
            "created_at": datetime.now(timezone.utc),
        })
        return "claimed"

    claim_result = claim_send(db.transaction())
    if claim_result != "claimed":
        raise HTTPException(
            status_code=404 if claim_result == "not_found" else 409,
            detail="Deletion request not found" if claim_result == "not_found" else "This request is already being sent or has been sent",
        )

    def record_send_failure(uncertain: bool) -> None:
        request_status = "SEND_UNCONFIRMED" if uncertain else "APPROVED_NOT_SENT"
        update_document("privacy_actions", action_id, {"request_status": request_status})
        create_document("audit_logs", {
            "user_id": owned_user_id,
            "privacy_action_id": action_id,
            "event_type": "REQUEST_SEND_UNCONFIRMED" if uncertain else "REQUEST_SEND_REJECTED",
            "details": (
                "Gmail sending outcome could not be confirmed. Check the Gmail sent folder before retrying."
                if uncertain
                else "Gmail rejected the approved request before confirming submission; no sent status was recorded."
            ),
            "created_at": datetime.now(timezone.utc),
        })

    try:
        credentials = gmail_credentials(claims["uid"])
        provider = GmailProvider(
            credentials=credentials,
            save_credentials=lambda updated: save_refreshed_credentials(claims["uid"], updated),
        )
        sent_message = provider.send_message(
            action["channel_email"],
            action["request_subject"],
            action["request_body"],
        )
    except HttpError as exc:
        status_code = getattr(exc.resp, "status", None)
        uncertain = status_code is None or status_code >= 500
        record_send_failure(uncertain)
        if uncertain:
            raise HTTPException(status_code=502, detail="Gmail's sending result is uncertain. Check the Sent folder before taking further action.") from exc
        raise HTTPException(status_code=409, detail="Gmail rejected the approved request. Check its API authorization before trying again.") from exc
    except (LookupError, GmailOAuthConfigurationError, GmailAuthorizationError) as exc:
        record_send_failure(uncertain=False)
        raise HTTPException(status_code=409, detail="Gmail did not send the request. Reconnect Gmail or check its API authorization, then try again.") from exc
    except Exception as exc:
        record_send_failure(uncertain=True)
        raise HTTPException(status_code=502, detail="Gmail's sending result is uncertain. Check the Sent folder before taking further action.") from exc

    now = datetime.now(timezone.utc)
    update_document("privacy_actions", action_id, {
        "request_status": "SENT_BY_PRIVORA",
        "tracking_source": "privora_gmail",
        "sent_at": now,
        "gmail_message_id": sent_message["message_id"],
        "gmail_thread_id": sent_message.get("thread_id"),
    })
    create_document("audit_logs", {
        "user_id": owned_user_id,
        "privacy_action_id": action_id,
        "event_type": "REQUEST_SENT_BY_PRIVORA",
        "details": "Gmail confirmed submission of the explicitly approved deletion request. This does not confirm provider receipt or account deletion.",
        "created_at": now,
    })
    return {
        "id": action_id,
        "request_status": "SENT_BY_PRIVORA",
        "reply_status": "NO_REPLY",
        "message": "Gmail confirmed sending. Provider receipt and account deletion are not confirmed.",
    }


@router.post("/{user_id}/{action_id}/tracking")
def update_deletion_request_tracking(
    payload: RequestTrackingUpdate,
    user_id: str,
    action_id: str = Path(min_length=1),
    claims: dict = Depends(get_current_user),
):
    validate_numeric_user_path(user_id)
    user = authorize_user_path(user_id, claims)
    owned_user_id = canonical_user_id(user)
    action = get_document("privacy_actions", action_id)
    if (
        action is None
        or str(action.get("user_id")) != str(owned_user_id)
        or action.get("action_type") != "DELETE_REQUEST_DRAFT"
    ):
        raise HTTPException(status_code=404, detail="Deletion request not found")
    if action.get("status") != "APPROVED":
        raise HTTPException(status_code=409, detail="Approve the draft before tracking an external request")
    previous_status = action.get("request_status")
    if payload.status == "SENT_BY_USER" and previous_status not in {"APPROVED_NOT_SENT", "SEND_UNCONFIRMED"}:
        raise HTTPException(status_code=409, detail="This request cannot be marked sent from its current status")
    if payload.status == "REPLY_RECEIVED" and previous_status not in {"SENT_BY_USER", "SENT_BY_PRIVORA"}:
        raise HTTPException(status_code=409, detail="Mark the request as sent before recording a reply")

    now = datetime.now(timezone.utc)
    updated = update_document(
        "privacy_actions",
        action_id,
        {
            "request_status": payload.status,
            "reply_status": "REPLY_RECEIVED" if payload.status == "REPLY_RECEIVED" else action.get("reply_status", "NO_REPLY"),
            "sent_at": now if payload.status == "SENT_BY_USER" else action.get("sent_at"),
            "reply_received_at": now if payload.status == "REPLY_RECEIVED" else action.get("reply_received_at"),
            "reply_note": payload.reply_note.strip() if payload.reply_note else action.get("reply_note"),
            "tracking_updated_at": now,
        },
    )
    create_document(
        "audit_logs",
        {
            "user_id": owned_user_id,
            "privacy_action_id": action_id,
            "event_type": "REQUEST_TRACKING_UPDATED",
            "details": f"User reported deletion request status: {payload.status}. Privora has not independently verified this status.",
            "created_at": now,
        },
    )
    return {
        "id": action_id,
        "request_status": updated["request_status"],
        "reply_status": updated["reply_status"],
        "message": "Status saved as user-reported; Privora has not independently verified it.",
    }


@router.post("/{user_id}/check-replies")
def check_privora_gmail_replies(
    user_id: str,
    claims: dict = Depends(get_current_user),
):
    """Match newer service-domain headers in threads Privora sent."""
    validate_numeric_user_path(user_id)
    user = authorize_user_path(user_id, claims)
    owned_user_id = canonical_user_id(user)
    actions = [
        action for action in get_user_actions(owned_user_id)
        if action.get("request_status") == "SENT_BY_PRIVORA"
        and action.get("reply_status") not in {"REPLY_CANDIDATE", "REPLY_RECEIVED"}
        and action.get("gmail_thread_id")
        and action.get("gmail_message_id")
        and action.get("channel_email")
    ][:10]
    if not actions:
        return {"checked": 0, "reply_candidates": 0, "message": "No eligible Gmail-sent requests to check."}

    try:
        credentials = gmail_credentials(claims["uid"])
    except (LookupError, GmailOAuthConfigurationError, GmailAuthorizationError):
        return {"checked": 0, "reply_candidates": 0, "message": "Connect or reconnect Gmail to check sent-request replies."}
    provider = GmailProvider(
        credentials=credentials,
        save_credentials=lambda updated: save_refreshed_credentials(claims["uid"], updated),
    )

    checked = 0
    candidates = 0
    for action in actions:
        try:
            messages = provider.fetch_thread_metadata(action["gmail_thread_id"])
        except (GmailAuthorizationError, HttpError):
            continue
        checked += 1
        sent_at = action.get("sent_at")
        if isinstance(sent_at, str):
            try:
                sent_at = datetime.fromisoformat(sent_at.replace("Z", "+00:00"))
            except ValueError:
                continue
        if not isinstance(sent_at, datetime):
            continue
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=timezone.utc)
        recipient_domain = action["channel_email"].rsplit("@", 1)[-1].lower().rstrip(".")
        matched_domain = None
        for message in messages:
            if str(message.get("id")) == str(action["gmail_message_id"]):
                continue
            try:
                message_time = datetime.fromtimestamp(
                    int(message.get("internalDate")) / 1000,
                    tz=timezone.utc,
                )
            except (TypeError, ValueError, OSError):
                continue
            if message_time <= sent_at:
                continue
            headers = {
                str(header.get("name", "")).casefold(): str(header.get("value", ""))
                for header in (message.get("payload", {}).get("headers") or [])
            }
            sender = parseaddr(headers.get("from", ""))[1].lower()
            if "@" not in sender:
                continue
            sender_domain = sender.rsplit("@", 1)[-1].rstrip(".")
            if sender_domain == recipient_domain or sender_domain.endswith(f".{recipient_domain}"):
                matched_domain = sender_domain
                break
        if not matched_domain:
            continue

        now = datetime.now(timezone.utc)
        update_document("privacy_actions", action["id"], {
            "reply_status": "REPLY_CANDIDATE",
            "reply_detection_source": "gmail_thread_metadata",
            "reply_candidate_at": now,
            "reply_sender_domain": matched_domain,
        })
        create_document("audit_logs", {
            "user_id": owned_user_id,
            "privacy_action_id": action["id"],
            "event_type": "GMAIL_REPLY_CANDIDATE_MATCHED",
            "details": "A newer message from the catalogued service domain was found in the Gmail thread. Confirm it is a reply; message content was not read.",
            "created_at": now,
        })
        candidates += 1

    return {
        "checked": checked,
        "reply_candidates": candidates,
        "message": "Gmail headers were checked. Any match is a candidate, not verified provider receipt; confirm it in Gmail.",
    }
