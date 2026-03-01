# SkyForge

`SkyForge` is an open-source project for `Hypixel Skyblock` players interested in making profit through `The Forge` in the `Dwarven Mines`.

It fetches item recipes and unlock requirements from the [Official Hypixel Wiki](https://wiki.hypixel.net/The_Forge) and live market prices from the [Official Hypixel API](https://api.hypixel.net), then ranks every craftable forge item by profit per hour based on current `Bazaar` and `Auction House` prices. Results are displayed in a browser UI that updates live as new data arrives.

This tool is especially useful for filling idle forge slots — even if you have no particular interest in forge items, there's usually free profit just sitting on those idle slots.

## Architecture

SkyForge runs as five Docker containers:

| Container | Role |
| ----------- | ------ |
| `db` | PostgreSQL database — stores forge recipe and item data |
| `db-api` | Flask REST API — intermediary between the database and other services |
| `scraper` | Fetches forge item recipes, durations and requirements from the Hypixel Wiki and writes them to the database |
| `calculator` | Reads forge data from the database, fetches live market prices from the Hypixel API, calculates profits and pushes results to the web service |
| `web` | FastAPI backend + Vue 3 frontend — serves the browser UI and broadcasts results to connected clients over WebSocket |

## Usage

The website is available at \[add link here once deployed\].

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
| `WIKI_SCRAPE_INTERVAL` | `3600` | Seconds between wiki scrapes (3600 for hourly, 86400 for daily) |

Edit these in `docker-compose.yml` or set them as environment variables in your deployment method.

## Web UI

The website has three tabs:

- **`Tracker`** - The main feature, shows the ranked list of forge items, and updates live as new data arrives.
- **`Guide`** - Has all the information necessary for using the tracker effectively.
- **`How does it work?`** - Explains the underlying logic and methodology.

## Contributing

Interested in contributing? See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions and guidelines.

## Disclaimer

This project is neither endorsed by nor affiliated with Hypixel. Use it at your own discretion.
