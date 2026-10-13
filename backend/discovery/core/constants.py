"""
Shared constants for the discovery module.
"""

DEFAULT_MAX_EMAILS = 100
MAX_EMAIL_BODY_LENGTH = 10_000

SANITIZED_FIELDS = (
    "service_name",
    "domain",
    "relationship",
    "source",
    "first_seen",
    "last_activity",
    "data_categories",
    "account_status",
)

# Discovery signals used by the email parser.
ACCOUNT_DISCOVERY_KEYWORDS = (
    "welcome",
    "verify your email",
    "confirm your email",
    "registration",
    "registered",
    "account created",
    "application submitted",
    "application received",
    "password reset",
    "course enrollment",
    "enrolled",
    "hackathon",
    "account",
    "certificate",
    "subscription",
    "membership",
    "profile created",
)

# Common words that can indicate the purpose of an account.
RELATIONSHIP_KEYWORDS = {
    "internship": (
        "internship",
        "intern",
        "placement",
        "job application",
        "career",
    ),
    "education": (
        "course",
        "course enrollment",
        "learning",
        "class",
        "university",
        "college",
        "student",
        "certificate",
    ),
    "hackathon": (
        "hackathon",
        "coding competition",
        "challenge",
        "competition",
    ),
    "professional": (
        "resume",
        "cv",
        "professional",
        "employment",
        "work experience",
        "job",
        "career",
    ),
    "shopping": (
        "order",
        "purchase",
        "shopping",
        "cart",
        "delivery",
        "invoice",
    ),
    "finance": (
        "bank",
        "payment",
        "transaction",
        "billing",
        "wallet",
        "card",
    ),
}

# Data categories that can be detected from account-related emails.
DATA_CATEGORY_KEYWORDS = {
    "identity": (
        "full name",
        "name",
        "date of birth",
        "dob",
        "identity",
        "government id",
    ),
    "contact": (
        "email",
        "phone",
        "mobile",
        "contact",
        "address",
    ),
    "professional": (
        "resume",
        "cv",
        "job",
        "internship",
        "experience",
        "employment",
        "portfolio",
    ),
    "academic": (
        "college",
        "university",
        "student",
        "degree",
        "certificate",
        "academic",
        "marks",
        "transcript",
    ),
    "financial": (
        "payment",
        "bank",
        "card",
        "transaction",
        "billing",
        "invoice",
    ),
}

GMAIL_DISCOVERY_QUERY = (
    "welcome OR "
    "\"verify your email\" OR "
    "registration OR "
    "\"account created\" OR "
    "\"password reset\" OR "
    "certificate OR "
    "subscription OR "
    "membership OR "
    "hackathon OR "
    "\"application received\""
)