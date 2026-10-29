
from fastapi import APIRouter

from ..core.firestore_store import list_documents
from ..services.service_metadata import metadata_for_service


router = APIRouter(
    prefix="/services",
    tags=["Services"],
)


@router.get("/")
def list_services():
    services = list_documents("services")
    services.sort(key=lambda service: str(service.get("name", "")).lower())

    results = []
    for service in services:
        metadata = metadata_for_service(
            name=service.get("name"),
            domain=service.get("domain"),
            website=service.get("website"),
        ) or {}
        results.append({
            "id": (
                int(service["id"])
                if str(service["id"]).isdigit()
                else service["id"]
            ),
            "name": service.get("name"),
            "website": service.get("website"),
            "purpose": metadata.get("purpose", service.get("purpose")),
            "purpose_source_url": metadata.get("purpose_source_url"),
            "deletion_channel_url": metadata.get(
                "deletion_channel_url",
                service.get("deletion_request_url") or service.get("privacy_url"),
            ),
            "deletion_channel_source_url": metadata.get("deletion_channel_source_url"),
            "deletion_channel_type": metadata.get(
                "deletion_channel_type", "catalogued_request_channel"
            ),
        })
    return results
