from typing import Any

from fastapi import APIRouter, Depends

from ..core.authentication import canonical_user_id, get_current_user, authorize_user_path


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me")
def get_authenticated_profile(
    claims: dict[str, Any] = Depends(get_current_user),
):
    user = authorize_user_path(claims["uid"], claims)
    return {
        "id": canonical_user_id(user),
        "uid": claims["uid"],
        "name": user.get("name", ""),
        "email": user.get("email", ""),
    }
