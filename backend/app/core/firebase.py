
import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore


BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CREDENTIALS_PATH = BACKEND_DIR / "firebase-credentials.json"


def get_firebase_app():
    """Initialize Firebase Admin from the configured private credential file."""
    try:
        return firebase_admin.get_app()
    except ValueError:
        credentials_path = Path(
            os.getenv(
                "FIREBASE_CREDENTIALS_PATH",
                str(DEFAULT_CREDENTIALS_PATH),
            )
        )

        if not credentials_path.is_absolute():
            credentials_path = BACKEND_DIR / credentials_path

        if not credentials_path.is_file():
            raise FileNotFoundError(
                f"Firebase credentials not found at: {credentials_path}"
            )

        credential = credentials.Certificate(str(credentials_path))
        return firebase_admin.initialize_app(credential)


def get_firestore_client():
    """Return Firestore for the configured Firebase app."""
    return firestore.client(app=get_firebase_app())
