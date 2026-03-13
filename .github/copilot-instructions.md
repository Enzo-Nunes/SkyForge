# SkyForge – Copilot Instructions

## Architecture Overview

Five Docker services communicate over an internal Docker network:

```
scraper --> db-api --> db (PostgreSQL)
                ^
calculator -----+-----> web --> browser (WebSocket)
```

- **`scraper`**: Scrapes the [Hypixel Wiki](https://wiki.hypixel.net/The_Forge) using `curl_cffi` (impersonates Firefox to avoid bot detection). Parses forge item recipes/durations/requirements and `PUT`s them to `db-api`. Runs on a configurable interval (`WIKI_SCRAPE_INTERVAL`).
- **`db-api`**: Flask REST API. The only service that talks to PostgreSQL (`psycopg2`). Exposes endpoints for forge items and AH sales records.
- **`calculator`**: Fetches forge data from `db-api`, fetches live prices from the Hypixel Bazaar + Auction House APIs, calculates `ForgeProfit` entries, then `POST`s results to `web`. Runs on `REFRESH_TIME` interval. Also runs `AHSalesTracker` in a background thread.
- **`web`**: FastAPI service that serves the Vue 3 frontend and broadcasts results to connected browsers over WebSocket (`/ws`). Receives results via `POST /results`.
- **`db`**: PostgreSQL 18, schema initialised at startup by `db-api/db.py:init_schema()`.

## Shared Types

All inter-service data contracts live in `common/types.py` as `TypedDict`s: `ForgePageItem`, `ForgeItemInfo`, `ForgeProfit`. When changing a data shape, update `common/types.py` first, then propagate to all services.

## Key Patterns

**Logging**: Each service configures its own named logger in its `main.py` entry point with `logger.propagate = False` to prevent handler duplication. Never add handlers in non-entrypoint modules (e.g. `db.py` - it only calls `logging.getLogger()`).

**Bazaar item name mapping**: Bazaar API returns `SNAKE_CASE` IDs that don't match wiki names. Hardcoded overrides live in `MarketPriceTracker._convert_name()` in `calculator/main.py`. When adding new forge items, check if a name override is needed.

**AH volume tracking**: `AHSalesTracker` polls `auctions_ended` every 60s and only counts `bin=True` auctions with a `buyer`. It resolves sold UUIDs against `MarketPriceTracker._auction_id_map` (populated during price fetching). After 7 days of uptime, volume numbers stabilise from estimates to actuals. The extrapolation formula is `volume = quantity × (604800 / uptime_seconds)`.

**WebSocket payload**: `web/main.py:ResultsPayload` is what the browser receives - `profits`, `calculated_at`, `uptime_seconds`. Changing this requires matching updates in `App.vue`.

## Developer Workflow

```bash
# Start full stack
docker compose up --build -d

# Rebuild only one service after changes
docker compose up --build -d calculator

# Tail logs for a specific service
docker compose logs -f calculator

# Clean restart (drops DB volume)
docker compose down -v && docker compose up --build -d
```

Pre-commit hooks (Ruff + Prettier) run automatically on `git commit` after `pre-commit install`. Ruff config is in `ruff.toml` (120 char line length, import sorting enabled, E722 ignored). Prettier config is in `.prettierrc.json` (tabs, 120 char width).

## Service URLs (internal Docker network)

| Service  | URL                    |
|----------|------------------------|
| `db-api` | `http://db-api:5000`   |
| `web`    | `http://web:8000`      |
| Host UI  | `http://localhost:8145` |

## Database Schema

Three tables for forge data: `forge_items`, `forge_recipes`, `forge_requirements` (all keyed by item name). One table for AH volume tracking: `ah_sale_batches` (append-only, queried with a 7-day rolling window). Schema is idempotent - defined in `db-api/db.py:init_schema()`.

## Frontend

Vue 3 with `<script setup>` Composition API. No build step needed for development (Vite handles it inside the `web` container). Components live in `web/frontend/src/components/`. WebSocket connection is managed in `App.vue`.
