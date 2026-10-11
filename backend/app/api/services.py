
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Service

router = APIRouter(
    prefix="/services",
    tags=["Services"],
)


@router.get("/")
def list_services(db: Session = Depends(get_db)):
    services = db.query(Service).order_by(Service.name).all()

    return [
        {
            "id": service.id,
            "name": service.name,
            "website": service.website,
            "purpose": service.purpose,
        }
        for service in services
    ]