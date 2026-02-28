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

Make sure you have [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed, then clone the repository and start everything:

```bash
git clone https://github.com/Enzo-Nunes/SkyForge.git
cd SkyForge
docker compose up --build
```

Open your browser at [http://localhost:8000](http://localhost:8000). The UI will show a loading spinner until the first calculation cycle completes, then populate the table automatically.

## Configuration

Intervals are configured via environment variables in `docker-compose.yml`:

| Variable | Container | Default | Description |
| ----------- | ----------- | --------- | ------------- |
| `REFRESH_TIME` | `calculator` | `120` | Seconds between profit calculation cycles |
| `WIKI_SCRAPE_INTERVAL` | `scraper` | `3600` | Seconds between wiki scrape cycles |

Edit the values in `docker-compose.yml` under the relevant service's `environment` block and restart the respective container for changes to take effect.

## Using the UI

### Tracker tab

The main table lists all forge items with a positive profit, ranked by **Profit / hour** by default. Click any numeric column header to re-sort; click again to reverse the order. The **#** column always reflects the Profit / hour rank regardless of how the table is sorted.

The filter sidebar on the left lets you narrow down results:

- **Collection dropdowns** — set each to your current level. Items requiring a higher level are hidden.
- **Max Cost** — maximum ingredient cost you're willing to spend per item. Check **No budget limit** to disable.

Filter settings are saved in your browser and restored on the next visit.

### Profit / hour vs. total Profit

**Profit / hour** is the default sort because forge slots are time-limited — finishing a quick item and starting another is usually better than waiting days for a single craft.

However, if you know you'll be away for a while (e.g. going to sleep) and the forge would finish well before you're back, sorting by **Profit** may be a better choice — the extra duration doesn't cost you anything if the slot would sit idle anyway.

## Notes

- Most forge ingredients and forged items trade on only one market (Bazaar or Auction House). For the few available on both, the calculator picks the cheaper source for ingredients and the higher source for sell value.
- On the Bazaar, prefer **Buy Orders** over Instant Buy for ingredients, and **Sell Orders** over Instant Sell for finished items — the price difference can be significant.
- Prices in the table are estimates based on live API data. Always check the actual market before making a large purchase.

## Disclaimer

This project is neither endorsed by nor affiliated with Hypixel. Use it at your own discretion.
