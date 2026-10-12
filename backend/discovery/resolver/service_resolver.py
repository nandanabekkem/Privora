from typing import Dict, Optional


class ServiceResolver:
    """
    Resolves discovered domains into recognizable service metadata.

    Known services use explicit metadata. Known subdomains resolve
    to their canonical service. Unknown services are preserved.
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
        """Resolve a domain to canonical service metadata."""
        normalized_domain = self._normalize_domain(domain)

        # Prefer exact matches before checking genuine subdomains.
        canonical_domain = None
        if normalized_domain in self.SERVICE_MAP:
             canonical_domain = normalized_domain
        else:
              for known_domain in self.SERVICE_MAP:
                   if normalized_domain.endswith("." + known_domain):
                         canonical_domain = known_domain
                         break

        if canonical_domain is not None:
            service = self.SERVICE_MAP[canonical_domain]
            return {
                "service_name": service["service_name"],
                "domain": canonical_domain,
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
        """Normalize casing, whitespace, and common www prefixes."""
        normalized = domain.lower().strip().rstrip(".")

        if normalized.startswith("www."):
            normalized = normalized[4:]

        return normalized

    
    def _generate_service_name(self, domain: str) -> str:
        """Generate a readable fallback name for unknown services."""
        if not domain:
            return "Unknown Service"

        labels = domain.split(".")

        # Use the first label for ordinary unknown domains.
        # If a known brand appears at the start of a deceptive
        # domain, avoid presenting it as that known service.
        if (
            len(labels) >= 3
            and labels[0] in {
                known.split(".")[0]
                for known in self.SERVICE_MAP
            }
            and ".".join(labels[:2]) in self.SERVICE_MAP
        ):
            name = " ".join(labels).replace("-", " ").replace("_", " ")
        else:
            name = labels[0]

        return name.replace("-", " ").replace("_", " ").title()
