"""Use cases for property operations."""

from datetime import datetime

from ..domain.constants import DEFAULT_CURRENCY
from ..domain.repositories import PropertyRepository


class PropertyUseCases:
    """Application use cases for physical property CRUD."""

    def __init__(self, property_repo: PropertyRepository):
        self._repo = property_repo

    def add_property(
        self,
        name: str,
        value: float,
        purchase_date: datetime | None = None,
        description: str = "",
        category: str = "Other",
        currency: str = DEFAULT_CURRENCY,
    ) -> None:
        """Add a new property."""
        if purchase_date is None:
            purchase_date = datetime.now()
        self._repo.add_property(
            name=name,
            value=value,
            purchase_date=purchase_date,
            description=description,
            category=category,
            currency=currency,
        )

    def get_all_properties(self) -> list[dict]:
        df = self._repo.get_all()
        return df.to_dicts()

    def delete_property(self, id: int) -> None:
        self._repo.delete(id)

    def update_property(
        self,
        id: int,
        name: str,
        value: float,
        purchase_date: datetime | None = None,
        description: str = "",
        category: str = "Other",
        currency: str = DEFAULT_CURRENCY,
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
