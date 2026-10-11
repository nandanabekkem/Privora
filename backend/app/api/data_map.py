from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Account, User


router = APIRouter(
    prefix="/data-map",
    tags=["Personal Data Map"],
)


@router.get("/{user_id}")
def get_data_map(
    user_id: int,
    db: Session = Depends(get_db),
):
    if user_id <= 0:
        raise HTTPException(
            status_code=422,
            detail="User ID must be a positive integer",
        )

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    accounts = (
        db.query(Account)
        .filter(Account.user_id == user_id)
        .order_by(Account.id)
        .all()
    )

    data_map = []

    for account in accounts:
        service = account.service

        data_records = [
            {
                "category": record.category,
                "description": record.description,
            }
            for record in account.data_records
        ]

        data_map.append(
            {
                "account_id": account.id,
                "service": service.name,
                "website": service.website,
                "status": account.status,
                "last_activity": account.last_activity,
                "data_records": data_records,
                "data_record_count": len(data_records),
            }
        )

    return {
        "user_id": user_id,
        "account_count": len(data_map),
        "accounts": data_map,
    }
