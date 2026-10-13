from fastapi import FastAPI

from discovery.api.routes import router as discovery_router

app = FastAPI(
    title="Privora API",
    description="Privacy-focused Personal Data Lifecycle Agent",
    version="0.1.0",
)

app.include_router(discovery_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "privora",
    }