from __future__ import annotations

from fastapi import APIRouter, Query

from ..core.config import config
from ..pipeline.discovery_pipeline import DiscoveryPipeline
from ..sources.email.provider import EmailProvider

router = APIRouter(
    prefix="/discovery",
    tags=["discovery"],
)


def _get_synthetic_pipeline() -> DiscoveryPipeline:
    return DiscoveryPipeline(
        email_provider=EmailProvider.synthetic(),
    )


def _get_gmail_pipeline() -> DiscoveryPipeline:
    return DiscoveryPipeline.from_gmail(
        credentials_path=config.gmail_credentials_path,
        token_path=config.gmail_token_path,
    )


@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "discovery",
    }


@router.post("/run")
def run_discovery(
    source: str = Query(
        default="synthetic",
        pattern="^(synthetic|gmail)$",
    ),
) -> dict[str, object]:
    if source == "gmail":
        pipeline = _get_gmail_pipeline()
    else:
        pipeline = _get_synthetic_pipeline()

    results = pipeline.run()

    return {
        "status": "success",
        "source": source,
        "count": len(results),
        "accounts": [
            result.model_dump(mode="json")
            for result in results
        ],
    }