from fastapi import FastAPI
from app.api import audit_logs
from fastapi.middleware.cors import CORSMiddleware

from app.api.services import router as services_router
from app.api.data_map import router as data_map_router
from app.api.dormant import router as dormant_router
from app.api.rules import router as rules_router
from app.api.policies import router as policies_router
from app.api.privacy_actions import router as privacy_actions_router

from discovery.api.routes import router as discovery_router


app = FastAPI(
    title="Privora API",
    description="Personal Data Lifecycle Agent Backend",
    version="0.1.0",
)

# Allow the local frontend to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8443",
        "http://127.0.0.1:8443",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(services_router)
app.include_router(data_map_router)
app.include_router(dormant_router)
app.include_router(rules_router)
app.include_router(policies_router)
app.include_router(privacy_actions_router)
app.include_router(audit_logs.router)
app.include_router(discovery_router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "Privora Backend",
    }
