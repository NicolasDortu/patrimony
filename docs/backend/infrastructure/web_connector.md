# Web connectors

Web connectors live in `infrastructure/integrations/web_connector/`. Each one
is a small Playwright-driven plugin that knows how to log into a single broker
or bank and download positions or cash data.

## `SiteConnector` — base class

```python
class SiteConnector(ABC):
    profile: ConnectorProfile          # static metadata (id, fields, mapping)

    @abstractmethod
    def fetch(
        self,
        credentials: dict[str, str],
        on_status: Callable[[str], None],
        on_user_input: Callable[[str], str],
        headless: bool,
    ) -> list[dict]: ...
```

`fetch` returns a list of raw row-dicts. The `WebConnectorService` then runs
those rows through the same import pipeline that `FileConnectorService` uses,
so the dedup, ticker enrichment and `AssetType` resolution behaviour is
identical between web and file imports.

`on_status(message)` lets the connector stream live progress messages to the
UI — typically wired into the notification toast queue.

`on_user_input(prompt)` is a blocking callback the connector can use to ask
for an OTP / 2FA code mid-flow. It returns the value the user typed.

`headless` mirrors the user's "show browser" setting. Headed mode is useful
during debugging and for sites that block headless Chrome.

## Built-in connectors

| Module | Site | Notes |
|---|---|---|
| `revolut.py` | Revolut | Cash + positions |
| `degiro.py` | DeGiro | Positions |
| `trade_republic.py` | Trade Republic | Positions |

The registry in the `web_connector/__init__.py` maps `profile.id` →
connector instance and is exposed as `SITE_CONNECTORS` for the DI container.

## Adding a new connector

1. Create `my_broker.py` next to the existing connectors.
2. Subclass `SiteConnector`, set `profile`, implement `fetch(...)`.
3. Add it to `SITE_CONNECTORS` in the package `__init__`.
4. Record an automation script with the helpers in
   `development/records/` to capture the correct selectors.

Stealth options (`playwright-stealth`) are enabled by default to reduce
fingerprinting.
