from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth
from firebase_admin.exceptions import FirebaseError

from .firebase import get_firebase_app
from .firestore_store import collection, get_document, list_by_field


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    """Verify a Firebase ID token and return its trusted claims."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A Firebase ID token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        firebase_app = get_firebase_app()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase authentication is not configured",
        ) from exc
    except FirebaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase authentication is unavailable",
        ) from exc

    try:
        claims = auth.verify_id_token(
            credentials.credentials,
            app=firebase_app,
            check_revoked=True,
        )
    except (FirebaseError, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase ID token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if not isinstance(claims.get("uid"), str) or not claims["uid"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase ID token has no user identity",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return claims


def _create_user_for_claims(claims: dict[str, Any]) -> dict[str, Any]:
    uid = claims["uid"]
    user_ref = collection("users").document(uid)
    snapshot = user_ref.get()

    if snapshot.exists:
        user = {"id": snapshot.id, **(snapshot.to_dict() or {})}
        if user.get("firebase_uid", uid) != uid:
            raise HTTPException(status_code=403, detail="User access denied")
        return user

    legacy_matches = list_by_field("users", "firebase_uid", uid)
    if legacy_matches:
        return legacy_matches[0]

    user = {
        "firebase_uid": uid,
        "email": claims.get("email", ""),
        "name": claims.get("name") or claims.get("email", "").split("@")[0],
    }
    user_ref.set(user)
    return {"id": uid, **user}


def authorize_user_path(
    user_id: str | int,
    claims: dict[str, Any],
) -> dict[str, Any]:
    """Resolve a path user ID only when it belongs to the verified UID."""
    uid = claims["uid"]
    requested_id = str(user_id)

    if requested_id == uid:
        return _create_user_for_claims(claims)

    user = get_document("users", requested_id)
    if user is None or user.get("firebase_uid") != uid:
        raise HTTPException(status_code=403, detail="User access denied")
    return user


def canonical_user_id(user: dict[str, Any]) -> int | str:
    value = user["id"]
    return int(value) if str(value).isdigit() else str(value)


def validate_numeric_user_path(user_id: str) -> None:
    try:
        numeric_id = int(user_id)
    except (TypeError, ValueError):
        return
    if numeric_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="User ID must be a positive integer",
        )
