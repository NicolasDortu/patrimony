"""Reference Controller - Thin delegate to ReferenceRepository."""


class ReferenceController:
    """Controller for securities reference data."""

    def __init__(self, reference_repo):
        self._reference_repo = reference_repo

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search securities reference by ticker or name."""
        if not query or len(query) < 1:
            return []
        return self._reference_repo.search(query, limit)
