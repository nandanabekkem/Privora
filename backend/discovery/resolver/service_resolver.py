from typing import Dict, Optional


class ServiceResolver:
    """
    Resolves discovered domains into recognizable service metadata.

    Known services use explicit metadata. Unknown services are still
    preserved instead of being discarded.
    """

    SERVICE_MAP: Dict[str, Dict[str, str]] = {
        "linkedin.com": {
            "service_name": "LinkedIn",
            "relationship": "professional",
        },
        "github.com": {
            "service_name": "GitHub",
            "relationship": "development",
        },
        "coursera.org": {
            "service_name": "Coursera",
            "relationship": "education",
        },
        "udemy.com": {
            "service_name": "Udemy",
            "relationship": "education",
        },
        "internshala.com": {
            "service_name": "Internshala",
            "relationship": "internship",
        },
        "unstop.com": {
            "service_name": "Unstop",
            "relationship": "hackathon",
        },
        "devpost.com": {
            "service_name": "Devpost",
            "relationship": "hackathon",
        },
        "amazon.in": {
            "service_name": "Amazon",
            "relationship": "shopping",
        },
        "flipkart.com": {
            "service_name": "Flipkart",
            "relationship": "shopping",
        },
        "swiggy.com": {
            "service_name": "Swiggy",
            "relationship": "shopping",
        },
        "zomato.com": {
            "service_name": "Zomato",
            "relationship": "shopping",
        },
    }

    def resolve(self, domain: str) -> Dict[str, Optional[str]]:
        """
        Resolve a domain into service metadata.
        """
        normalized_domain = self._normalize_domain(domain)

        service = self.SERVICE_MAP.get(normalized_domain)

        if service:
            return {
                "service_name": service["service_name"],
                "domain": normalized_domain,
                "relationship": service["relationship"],
            }

        return {
            "service_name": self._generate_service_name(
                normalized_domain
            ),
            "domain": normalized_domain,
            "relationship": None,
        }

    def _normalize_domain(self, domain: str) -> str:
        """
        Normalize common domain variations.
        """
        normalized = domain.lower().strip()

        if normalized.startswith("www."):
            normalized = normalized[4:]

        return normalized

    def _generate_service_name(self, domain: str) -> str:
        """
        Generate a readable fallback name for unknown services.
        """
        name = domain.split(".")[0]

        if not name:
            return "Unknown Service"

        return name.replace("-", " ").replace("_", " ").title()