
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import Service


sample_services = [
    {
        "name": "Google",
        "website": "https://google.com",
        "purpose": "Search, email, cloud storage, and other online services",
    },
    {
        "name": "Instagram",
        "website": "https://instagram.com",
        "purpose": "Photo and video sharing",
    },
    {
        "name": "LinkedIn",
        "website": "https://linkedin.com",
        "purpose": "Professional networking and career services",
    },
    {
        "name": "Microsoft",
        "website": "https://microsoft.com",
        "purpose": "Productivity tools, email, and cloud services",
    },
    {
        "name": "GitHub",
        "website": "https://github.com",
        "purpose": "Code hosting and software collaboration",
    },
]


def seed_services():
    with SessionLocal() as db:
        for item in sample_services:
            existing = db.scalar(
                select(Service).where(Service.name == item["name"])
            )

            if existing is None:
                db.add(Service(**item))

        db.commit()
        print("Sample services added successfully!")


if __name__ == "__main__":
    seed_services()