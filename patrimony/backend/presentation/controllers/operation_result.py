from typing import Optional
from dataclasses import dataclass


@dataclass(slots=True)
class OperationResult:
    """Generic result for operations."""

    success: bool
    message: str
    data: Optional[dict] = None
