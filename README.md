# SkyForge

`SkyForge` is an open-source project for `Hypixel Skyblock` players interested in making profit through `The Forge` in the `Dwarven Mines`.

It loads item recipes and unlock requirements from a versioned JSON dataset and live market prices from the [Official Hypixel API](https://api.hypixel.net), then ranks every craftable forge item by profit per hour based on current `Bazaar` and `Auction House` prices. Results are displayed in a browser UI that updates live as new data arrives.

This tool is especially useful for filling idle forge slots - even if you have no particular interest in forge items, there's usually free profit just sitting on those idle slots.

## Architecture

SkyForge runs as four Docker containers:

| Container | Role |
| ----------- | ------ |
| `db` | PostgreSQL database - stores forge recipe and item data |
| `db-api` | FastAPI REST API - intermediary between the database and other services, and loads forge data from `db-api/forge_data.json` at startup |
| `calculator` | Reads forge data from the database, polls Bazaar/Auction House data from the Hypixel API, tracks market history, calculates profits and pushes results to the web service |
| `web` | FastAPI backend + Vue 3 frontend - serves the browser UI and broadcasts results to connected clients over WebSocket |

## Usage

The website is available at \[app.skyforgetracker.com\].

If you want to run locally, make sure you have [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed, then clone the repository and start everything:

```bash
git clone https://github.com/Enzo-Nunes/SkyForge.git
cd SkyForge
docker compose up --build
```

Open your browser at [http://localhost:8145](http://localhost:8145). The UI will show a loading spinner until the first calculation cycle completes, then populate the table automatically.

## Configuration

Environment variables control SkyForge's behavior:

| Variable | Default | Description |
| ----------- | --------- | ------------- |
| `POSTGRES_PASSWORD` | `skyforge` | Database password. |
| `REFRESH_TIME` | `120` | Seconds between profit calculation cycles (120-600 recommended) |
| `LISTING_REFRESH_TIME` | `45` | Seconds between Auction House listing snapshots used to track BIN UUID/price state. |
| `ENDED_AUCTIONS_REFRESH_TIME` | `60` | Seconds between polling the ended-auctions feed used to record realized AH sales. |
| `AH_STATE_STALE_SECONDS` | `900` | Maximum age for unseen AH listing state entries before pruning. |
| `AH_STATE_END_GRACE_SECONDS` | `180` | Extra grace period after auction end time before stale-pruning listing state. |

## Market History and Stats

SkyForge stores recent market history in PostgreSQL and computes 7-day stats used by the tracker UI:

- **Auction House (AH)**: records realized BIN sales from ended auctions.
- **Bazaar**: records periodic snapshots of forge-item sell price and weekly volume.

From that history, SkyForge computes low/high/median and sample counts over the latest 7 days.

AH weekly volume is extrapolated only during partial uptime and only when an item has at least 3 observed AH sales;
otherwise SkyForge shows observed counts without extrapolation.

Forge item metadata is loaded from `db-api/forge_data.json`, which is created and maintained separately from the SkyForge runtime stack.
If this crafting dataset becomes outdated, contributions updating `db-api/forge_data.json` are welcome.

## Web UI

The website has three tabs:

- **`Tracker`** - The main feature, shows the ranked list of forge items, and updates live as new data arrives.
- **`Guide`** - Has all the information necessary for using the tracker effectively.
- **`How does it work?`** - Explains the underlying logic and methodology.

## Contributing

Interested in contributing? See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions and guidelines.

## Disclaimer

This project is neither endorsed by nor affiliated with Hypixel. Use it at your own discretion.
