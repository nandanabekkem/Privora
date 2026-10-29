from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class DataCategory(str, Enum):
    IDENTITY = "identity"
    CONTACT = "contact"
    PROFESSIONAL = "professional"
    ACADEMIC = "academic"
    FINANCIAL = "financial"
    OTHER = "other"


class AccountStatus(str, Enum):
    ACTIVE = "active"
    DORMANT = "dormant"
    UNKNOWN = "unknown"


class DiscoverySource(str, Enum):
    EMAIL = "email"
    PASSWORD_MANAGER = "password_manager"
    BROWSER = "browser"
    ACCOUNT_EXPORT = "account_export"


class DiscoveredAccount(BaseModel):
    service_name: str = Field(..., min_length=1)
    domain: str = Field(..., min_length=1)

    relationship: Optional[str] = None

    source: DiscoverySource

    first_seen: Optional[datetime] = None
    last_activity: Optional[datetime] = None

    data_categories: List[DataCategory] = Field(default_factory=list)

    account_status: AccountStatus = AccountStatus.UNKNOWN
    evidence: List[str] = Field(default_factory=list)


class SanitizedAccountContext(BaseModel):
    service_name: str
    domain: str
    relationship: Optional[str] = None

    source: DiscoverySource

    first_seen: Optional[datetime] = None
    last_activity: Optional[datetime] = None

    data_categories: List[DataCategory] = Field(default_factory=list)

    account_status: AccountStatus = AccountStatus.UNKNOWN
