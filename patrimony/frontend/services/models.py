"""Frontend data models for the service layer."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ...backend.domain.entities import AssetType, EntryType


@dataclass(slots=True)
class OperationResult:
    """Generic result for mutation operations."""

    success: bool
    message: str
    data: Optional[dict] = None


@dataclass(slots=True)
class SecurityPosition:
    """Frontend model for individual security position."""

    id: Optional[int] = None
    ticker: str = ""
    price: float = 0.0
    quantity: float = 1.0
    fees: float = 0.0
    entry_type: EntryType = EntryType.MANUAL
    date: datetime = field(default_factory=datetime.now)
    asset_type: AssetType = AssetType.STOCK


@dataclass(slots=True)
class SecurityTotal:
    """Frontend model for aggregated security positions."""

    ticker: str = ""
    total_quantity: float = 0.0
    avg_price: float = 0.0
    current_price: float = 0.0
    total_value: float = 0.0
    asset_type: str = "STOCK"


@dataclass(slots=True)
class Property:
    """Frontend model for a physical property."""

    id: Optional[int] = None
    name: str = ""
    description: str = ""
    value: float = 0.0
    purchase_date: datetime = field(default_factory=datetime.now)
    category: str = "Other"
    currency: str = "EUR"
    entry_type: str = "MANUAL"
