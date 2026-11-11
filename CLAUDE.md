# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

SkyForge ranks Hypixel Skyblock forge items by profit per hour from live Bazaar and Auction House (AH) prices. It runs as four Docker Compose services: `db` (PostgreSQL), `db-api`, `calculator`, and `web` (FastAPI + Vue 3).

## Commands

There is no test suite. CI (`.github/workflows/ci.yml`) checks three things: pre-commit hooks, that each image builds, and that the whole stack boots with no container exiting.

```bash
# Lint and format everything (exactly what CI runs). Ruff for Python, Prettier for Vue/JS/HTML/YAML.
pre-commit run --all-files

# Python only, faster
ruff check --fix . && ruff format .

# Run the stack; UI at http://localhost:8145
docker compose up --build -d

# Rebuild one service after changing it (db-api | calculator | web)
docker compose up --build -d calculator

docker compose logs -f calculator

# Validate compose file; wipe volumes for a clean slate (this deletes the 7-day market history)
docker compose config -q
docker compose down -v

# Only `web` publishes a port. Reach the others from inside the network:
docker compose exec db psql -U skyforge skyforge
```

Frontend (`web/frontend`): `npm ci`, `npm run build`. `npm run dev` starts Vite, but `vite.config.js` has no proxy, so `/ws` has no backend and the tracker stays on its loading spinner. To see live data, rebuild the `web` service instead.

## Architecture

Data flows one way:

```
forge_data.json ─► db-api ◄─► PostgreSQL
                     ▲
                     │ HTTP (forge items, sales, snapshots, 7-day summary)
Hypixel API ─► calculator ─► POST /results ─► web ─► WebSocket /ws ─► browser
```

- **db-api** (`db-api/`) is the only service that talks to PostgreSQL. `db.py` holds all SQL; `db_runtime.py` opens a fresh connection per operation and turns connection failures into a 503. On every startup it creates missing tables and **deletes and reloads all forge item tables from `forge_data.json`**, so that file is the source of truth and editing it means rebuilding `db-api`.
- **calculator** (`calculator/`) is a plain Python process with three loops:
  - `MarketListingUpdater` thread: every `LISTING_REFRESH_TIME` seconds, scans every AH page into an in-memory `auction_id -> (item, price, last_seen)` map and posts Bazaar sell-price snapshots to db-api.
  - `AHSalesTracker` thread: polls Hypixel's `auctions_ended`, matches sold auction IDs against that map, and posts the sales to db-api.
  - Main loop: every `REFRESH_TIME` seconds, re-fetches forge items, prices everything, and publishes the ranked list to `web`.
- **web** (`web/main.py`) keeps only the latest payload in memory, sends it to each browser on connect, and broadcasts each new one. It never touches the database. The built Vue app is served as static files from the same process.

### Things that span files

- **Items are keyed by display name everywhere** (`"Fine Amber Gemstone"`), matching the keys in `forge_data.json`. AH listings already use display names. Bazaar product IDs are converted by `MarketPriceTracker._convert_name` (`NAME_OVERRIDES`, `SUFFIX_REPLACEMENTS`). An item whose Bazaar ID does not convert to its `forge_data.json` name is silently treated as an AH item, so a missing price usually means a name mismatch.
- **Pricing rule** (`profit_calculator.py`): a material or product is priced from the Bazaar if the Bazaar has it, otherwise from the lowest BIN on the AH. `Coins` is a pseudo-material worth 1. Items that cannot be fully priced, or that are not profitable, are dropped from the output rather than shown.
- **Pets**: the AH lists them as `[Lvl N] Name`. Only level 1 Legendary listings are mapped to `"<Name> Pet"`, because that is what the forge produces.
- **`Duration` is in hours** in `forge_data.json` and the `duration_hours` column.
- **The result row shape is a wire contract.** `ForgeProfit` in `calculator/calc_types.py` uses keys with spaces (`"Profit per Hour"`, `"Sell Price Range % 7d"`). `web` passes the dicts through untyped, and `TrackerTab.vue` reads the same keys. Change both ends together.
- **Requirement filters are hard-coded.** `REQUIREMENTS` in `TrackerTab.vue` lists each requirement name and its max level. A new requirement key in `forge_data.json` needs an entry there or it cannot be filtered.
- **AH volume and coverage.** Each successful `auctions_ended` poll is posted to `/ah-sales` even when it found no sales, because db-api logs every poll in `ah_polls`. Coverage (seconds of the last 7 days actually watched) is computed from those rows in `read_market_summary_7d`. Volume is extrapolated to a full week only when coverage is below 7 days and the item has at least 3 observed sales (`MIN_AH_SALES_FOR_EXTRAPOLATION`); coverage of 99% or more counts as a full week (`FULL_COVERAGE_RATIO`). The sales tracker skips a poll when the listing map is stale, so that unmatched time is not counted as coverage.
- **`LISTING_REFRESH_TIME` is clamped to 59s** because `auctions_ended` only covers the last 60 seconds; slower polling loses sales.
- **`/results` auth.** `web` writes a random token to the shared `results_token` volume each time it starts; the calculator re-reads it on every publish. `/results` is on the public port, so keep the check.
- **History retention** is 8 days, pruned on each insert. Schema setup is `CREATE TABLE IF NOT EXISTS` only; there are no migrations, so changing an existing table needs a manual migration or `down -v`.

### Imports and builds

Every image builds from the repository root (`context: .`). Each service's `.py` files are copied flat into `/app`, so modules import their siblings by bare name (`from calc_http import ...`, `import db`). `common/` is copied in as a package for `db-api` and `calculator` only; `web` does not get it. Ruff's import sorter therefore groups sibling modules with third-party imports and puts `common` in its own first-party block.

Images use Python 3.15. `VERSION` is baked into the frontend at build time as `VITE_APP_VERSION`.

## Conventions

- Branch from `dev` and open PRs against `dev`. `main` is for releases.
- Do not edit `VERSION` by hand. Labelling a PR to `main` with `major`, `minor` or `patch` bumps it, and a push to `main` that changes `VERSION` creates the tag and GitHub release.
- When tracker logic or what the UI shows changes, update the in-app explanations in `web/frontend/src/components/GuideTab.vue` and `HowTab.vue`, and the "Market History and Stats" section of `README.md`. CONTRIBUTING.md asks that the AH and Bazaar history behaviours described there stay as they are unless a PR says it is changing them.
- Formatting: Python line length 120. Prettier uses tabs and width 120, except YAML (2 spaces).
- No `print()` or `console.log()` debugging left in; services log through their named logger.
