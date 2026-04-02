# Patrimony

An open-source personal wealth tracking desktop application built with **Reflex** (Python) and **Tauri** (Rust).

## Features

- **Securities tracking** – Add stock, ETF, crypto and commodity positions manually or via file import (CSV/Excel). Aggregated view with current prices, allocation charts and heatmap.
- **Cash accounts** – Track bank accounts with balance operations, monthly income/expense charts and category breakdowns.
- **Portfolio overview** – Unified dashboard with total wealth, performance KPIs, wealth chart, top/bottom performers and dividend summary.
- **File connectors** – Import positions or cash operations from CSV/Excel files with a column-mapping wizard. Automatic duplicate detection via row hashing.
- **Web connectors** – Automated browser-based import from broker/bank websites using Playwright with profile-based automation steps.
- **Multi-currency** – All values converted to a user-selected display currency via live exchange rates.
- **Market data** – Live and historical prices from Yahoo Finance with local DuckDB cache (15-min TTL for current prices, smart gap-fill for history).
- **Credential vault** – Encrypted storage for web connector credentials (PBKDF2 + Fernet), unlockable with a master password.
- **Internationalisation** – English, French and Spanish locale files.
- **Dark/light theme** – Configurable accent and asset-type colours.

## Architecture

```
patrimony/
├─ backend/               # Pure Python business logic
│  ├─ domain/             # Entities, repository ABCs, services
│  │  └─ services/        # Portfolio, securities, currency, file & web connector
│  ├─ infrastructure/     # Implementations
│  │  ├─ database/        # DuckDB connection, DDL, reference data
│  │  ├─ integrations/    # yfinance provider, Playwright connector, file reader
│  │  └─ repositories/    # All repository implementations
│  └─ presentation/       # DI container (dependency-injector)
├─ frontend/              # Reflex UI layer
│  ├─ components/         # Reusable components (card, loading, notification, …)
│  ├─ config/             # File connector path store (JSON)
│  ├─ dialogs/            # Add/edit dialogs for positions, cash, dividends
│  ├─ languages/locale/   # i18n JSON files
│  ├─ pages/              # Route pages (index, securities, cash, connectors, …)
│  ├─ states/             # Reflex state classes per page/feature
│  ├─ styles/             # Global CSS-in-Python styles
│  ├─ templates/          # Page template wrapper with sidebar and theme state
│  ├─ views/              # Charts, tables, KPIs, pickers
│  ├─ services.py         # Single interface between frontend and backend
│  └─ logging_config.py   # Frontend logging + event collector
src-tauri/                # Tauri v2 desktop shell (Rust)
```

The frontend **never** imports the backend directly — all calls go through `frontend/services.py` which consumes the DI container.

## Tech stack

| Layer | Technology |
|-------|-----------|
| UI framework | [Reflex](https://reflex.dev/) (Python) |
| Desktop shell | [Tauri v2](https://v2.tauri.app/) (Rust) |
| Database | [DuckDB](https://duckdb.org/) (embedded) |
| DataFrames | [Polars](https://www.pola.rs/) |
| Market data | [yfinance](https://github.com/ranaroussi/yfinance) |
| Web scraping | [Playwright](https://playwright.dev/python/) |
| Encryption | [cryptography](https://cryptography.io/) (Fernet/PBKDF2) |
| DI | [dependency-injector](https://python-dependency-injector.ets-labs.org/) |

## Prerequisites

- **Python ≥ 3.13**
- **Rust** (stable) – required by Tauri
- **uv** – Python package manager ([install](https://docs.astral.sh/uv/getting-started/installation/))
- **Node.js** – required by Reflex's frontend build

## Getting started

```bash
# Clone the repository
git clone https://github.com/NicolasDortu/patrimony.git
cd patrimony

# Install Python dependencies
uv sync

# Install Playwright browsers (needed for web connectors)
uv run playwright install chromium

# Run in development mode (starts both Reflex and Tauri)
cargo tauri dev
```

`cargo tauri dev` automatically runs `uv run reflex run` as part of its `beforeDevCommand` (configured in `src-tauri/tauri.conf.json`), then opens the Tauri window pointing at `localhost:3000`.

## Building for production

```bash
cargo tauri build
```

The bundled application will be in `src-tauri/target/release/bundle/`.

## License

Open source.