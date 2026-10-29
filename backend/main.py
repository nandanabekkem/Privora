"""Backward-compatible entry point for the complete application.

Supports ``uvicorn main:app`` from ``backend/`` and
``uvicorn backend.main:app`` from the repository root.
"""

if __package__ == "backend":
    from backend.app.main import app
else:
    from app.main import app
