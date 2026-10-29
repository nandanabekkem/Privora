from fastapi import Depends, FastAPI
from .core.config import settings
from .api import audit_logs
from fastapi.middleware.cors import CORSMiddleware

from .api.services import router as services_router
from .api.data_map import router as data_map_router
from .api.dormant import router as dormant_router
from .api.rules import router as rules_router
from .api.policies import router as policies_router
from .api.privacy_actions import router as privacy_actions_router
from .api.analysis import router as analysis_router
from .api.assistant import router as assistant_router

if __package__ == "app":
    from discovery.api.routes import router as discovery_router
else:
    from ..discovery.api.routes import router as discovery_router

from .api.auth import router as auth_router
from .core.authentication import get_current_user


app = FastAPI(
    title="Privora API",
    description="Personal Data Lifecycle Agent Backend",
    version="0.1.0",
)

# Allow only explicitly configured frontend origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.PRIVORA_CORS_ORIGINS.split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(auth_router)
app.include_router(services_router, dependencies=[Depends(get_current_user)])
app.include_router(data_map_router)
app.include_router(dormant_router)
app.include_router(rules_router)
app.include_router(policies_router)
app.include_router(privacy_actions_router)
app.include_router(analysis_router)
app.include_router(assistant_router)
app.include_router(audit_logs.router)
app.include_router(discovery_router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "Privora Backend",
    }
