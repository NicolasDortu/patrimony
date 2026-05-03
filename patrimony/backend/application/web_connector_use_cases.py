"""Use cases for browser-based web connector operations."""

from collections.abc import Callable

from ..domain.services.connectors import (
    WebConnectorService as WebConnectorDomainService,
)


class WebConnectorUseCases:
    """Application use cases for web connector operations."""

    def __init__(self, web_connector_service: WebConnectorDomainService):
        self._web_connector_service = web_connector_service

    def list_web_profiles(self) -> list[dict]:
        """Return all available web connector profiles as dicts."""
        profiles = self._web_connector_service.list_profiles()
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "import_mode": p.import_mode,
                "needs_matching": p.needs_matching,
                "credential_fields": [
                    {
                        "placeholder": f[0],
                        "label": f[1],
                        "type": (
                            "select"
                            if len(f) > 2
                            else "password"
                            if "password" in f[1].lower()
                            else "text"
                        ),
                        "options": list(f[2]) if len(f) > 2 else [],
                    }
                    for f in p.credential_fields
                ]
                if p.credential_fields
                else [],
            }
            for p in profiles
        ]

    def run_web_connector(
        self,
        profile_id: str,
        credentials: dict[str, str],
        on_user_input: Callable[[str, str], str] | None = None,
        headless: bool = False,
    ) -> dict:
        """Execute a web connector profile. Returns result dict with import data."""
        result = self._web_connector_service.run_connector(
            profile_id,
            credentials,
            on_user_input=on_user_input,
            headless=headless,
        )
        return {
            "success": result.success,
            "imported": result.imported,
            "skipped": result.skipped,
            "errors": result.errors,
            "status_log": result.status_log,
            "needs_matching": result.needs_matching,
            "unmatched_positions": result.unmatched_positions,
        }

    def get_web_profile(self, profile_id: str):
        return self._web_connector_service.get_profile(profile_id)

    def import_matched_positions(self, matched: list[dict]) -> dict:
        """Import user-matched positions from a web connector."""
        result = self._web_connector_service.import_matched_positions(matched)
        return {
            "success": result.success,
            "imported": result.imported,
            "skipped": result.skipped,
            "errors": result.errors,
        }
