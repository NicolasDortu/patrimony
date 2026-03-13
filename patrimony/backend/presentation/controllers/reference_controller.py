"""Reference Controller - Search securities reference data."""

from ..di_container import container


class ReferenceController:
    """Controller for securities reference data."""

    @property
    def _reference_repo(self):
        """Get reference repository from DI container."""
        return container.reference_repository()

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search securities reference by ticker or name."""
        if not query or len(query) < 1:
            return []
        return self._reference_repo.search(query, limit)
