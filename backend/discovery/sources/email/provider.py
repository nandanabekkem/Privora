from __future__ import annotations

from typing import Any

from ..base import DiscoverySource


class EmailProvider(DiscoverySource):
    def __init__(
        self,
        emails: list[dict[str, Any]] | None = None,
    ) -> None:
        self.emails = emails or []

    def fetch_records(self) -> list[dict[str, Any]]:
        return self.emails

    @classmethod
    def synthetic(cls) -> "EmailProvider":
        return cls(
            [
                {
                    "sender": "noreply@github.com",
                    "subject": "Welcome to GitHub",
                    "timestamp": "2026-09-01T10:30:00",
                    "body": (
                        "Welcome to GitHub. "
                        "Your account has been created."
                    ),
                },
                {
                    "sender": "security@github.com",
                    "subject": "New sign-in to your GitHub account",
                    "timestamp": "2026-10-02T14:20:00",
                    "body": (
                        "Your GitHub account was accessed "
                        "successfully."
                    ),
                },
                {
                    "sender": "notifications@linkedin.com",
                    "subject": "Welcome to LinkedIn",
                    "timestamp": "2025-02-10T09:15:00",
                    "body": (
                        "Your professional profile has been created."
                    ),
                },
                {
                    "sender": "security@linkedin.com",
                    "subject": "LinkedIn password reset",
                    "timestamp": "2025-08-15T11:00:00",
                    "body": (
                        "A password reset was requested "
                        "for your LinkedIn account."
                    ),
                },
                {
                    "sender": "billing@example-service.com",
                    "subject": "Payment confirmation",
                    "timestamp": "2024-03-20T16:45:00",
                    "body": (
                        "Your payment was processed successfully. "
                        "Your billing information is stored."
                    ),
                },
                {
                    "sender": "hello@example-service.com",
                    "subject": "Registration successful",
                    "timestamp": "2024-03-18T10:00:00",
                    "body": (
                        "Your registration was successful."
                    ),
                },
                {
                    "sender": "no-reply@coursera.org",
                    "subject": "Certificate available",
                    "timestamp": "2025-06-12T13:00:00",
                    "body": (
                        "Your course certificate is now available."
                    ),
                },
                {
                    "sender": "notifications@internshala.com",
                    "subject": "Internship application submitted",
                    "timestamp": "2026-07-12T15:30:00",
                    "body": (
                        "Your internship application was submitted. "
                        "Your name, email, phone, resume, education, "
                        "college, and work experience were provided."
                    ),
                },
                {
                    "sender": "notifications@unstop.com",
                    "subject": "Hackathon registration successful",
                    "timestamp": "2026-08-05T12:00:00",
                    "body": (
                        "Your hackathon registration was successful. "
                        "Your name and email were used."
                    ),
                },
                {
                    "sender": "no-reply@amazon.in",
                    "subject": "Welcome to Amazon",
                    "timestamp": "2026-05-18T09:00:00",
                    "body": (
                        "Your Amazon account has been created."
                    ),
                },
                {
                    "sender": "hello@devpost.com",
                    "subject": "Welcome to Devpost",
                    "timestamp": "2026-06-10T10:00:00",
                    "body": (
                        "Your Devpost account has been created."
                    ),
                },
                {
                    "sender": "offers@randomshop.com",
                    "subject": "Weekend offers",
                    "timestamp": "2026-09-20T12:00:00",
                    "body": (
                        "Check out our latest weekend offers."
                    ),
                },
                {
                    "sender": "newsletter@technews.com",
                    "subject": "Weekly technology newsletter",
                    "timestamp": "2026-09-21T08:00:00",
                    "body": (
                        "Here are this week's technology stories."
                    ),
                },
            ]
        )

    @classmethod
    def from_records(
        cls,
        records: list[dict[str, Any]],
    ) -> "EmailProvider":
        return cls(records)