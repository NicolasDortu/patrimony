"""Use cases for property operations."""

from datetime import datetime
from typing import Optional

from ..domain.repositories import PropertyRepository


class PropertyUseCases:
    """Application use cases for physical property CRUD."""

    def __init__(self, property_repo: PropertyRepository):
        self._repo = property_repo

    def add_property(
        self,
        name: str,
        value: float,
        purchase_date: Optional[datetime] = None,
        description: str = "",
        category: str = "Other",
        currency: str = "EUR",
    ) -> dict:
        """Add a new property. Returns {'id': int}."""
        if purchase_date is None:
            purchase_date = datetime.now()
        prop_id = self._repo.add_property(
            name=name,
            value=value,
            purchase_date=purchase_date,
            description=description,
            category=category,
            currency=currency,
        )
        return {"id": prop_id}

    def get_all_properties(self) -> list[dict]:
        df = self._repo.get_all()
        return df.to_dicts() if df is not None else []

    def delete_property(self, id: int) -> None:
        self._repo.delete(id)

    def update_property(
        self,
        id: int,
        name: str,
        value: float,
        purchase_date: Optional[datetime] = None,
        description: str = "",
        category: str = "Other",
        currency: str = "EUR",
    ) -> None:
        if purchase_date is None:
            purchase_date = datetime.now()
        self._repo.update_property(
            id=id,
            name=name,
            value=value,
            purchase_date=purchase_date,
            description=description,
            category=category,
            currency=currency,
        )
