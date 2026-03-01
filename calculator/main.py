import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone
from math import ceil
from typing import cast

import requests

from common.types import ForgeItemInfo, ForgeProfit

DB_API_URL = "http://db-api:5000"
WEB_URL = "http://web:8000"


def wait_for_api(logger: logging.Logger, retries: int = 10, delay: int = 3) -> None:
    for attempt in range(retries):
        try:
            requests.get(f"{DB_API_URL}/health", timeout=5)
            return
        except requests.exceptions.ConnectionError:
            if attempt < retries - 1:
                logger.info(f"db-api not ready (attempt {attempt + 1}/{retries}), retrying in {delay}s...")
                time.sleep(delay)
            else:
                raise RuntimeError(f"Could not connect to db-api after {retries} attempts")


class MarketPriceTracker:
    BAZAAR_URL = "https://api.hypixel.net/v2/skyblock/bazaar"
    AUCTION_HOUSE_URL = "https://api.hypixel.net/v2/skyblock/auctions"
    HEADERS = {"Content-Type": "application/json"}

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self._auction_id_map: dict[str, tuple[str, float]] = {}  # auction_id -> (item_name, inserted_at)
        self._auction_id_map_lock = threading.Lock()

    def fetch_auction_house_prices(self) -> dict[str, int]:
        response = requests.get(self.AUCTION_HOUSE_URL, headers=self.HEADERS)
        response.raise_for_status()
        auction_house = response.json()
        pages = auction_house["totalPages"]
        items = auction_house["totalAuctions"]

        self._logger.info(f"Starting Auction House processing, {pages} pages found with a total of {items} auctions:")
        prices: dict[str, int] = {}
        new_id_map: dict[str, str] = {}

        for i in range(pages):
            try:
                page_response = requests.get(self.AUCTION_HOUSE_URL, headers=self.HEADERS, params={"page": i})
                page_response.raise_for_status()
                page = page_response.json()
            except Exception as e:
                self._logger.warning(f"Skipping AH page {i}: {e}")
                continue
            for auction in page.get("auctions", []):
                item_name = auction["item_name"]
                new_id_map[auction["uuid"]] = item_name
                current_price = prices.get(item_name, -1)
                new_price = auction["starting_bid"]
                if auction["bin"] and (current_price == -1 or current_price > new_price):
                    prices[item_name] = new_price

        self._update_auction_id_map(new_id_map)

        self._logger.info("Auction House processing complete.")
        return prices

    def _update_auction_id_map(self, new_entries: dict[str, str]) -> None:
        """Accumulate new uuid→item_name entries with a timestamp (called from main thread)."""
        now = time.monotonic()
        with self._auction_id_map_lock:
            for uuid, name in new_entries.items():
                self._auction_id_map[uuid] = (name, now)

    def resolve_and_remove(self, auction_ids: list[str]) -> dict[str, str]:
        """Look up item names for the given auction IDs, remove matched entries, and return {uuid: item_name}."""
        result: dict[str, str] = {}
        with self._auction_id_map_lock:
            for auction_id in auction_ids:
                entry = self._auction_id_map.pop(auction_id, None)
                if entry:
                    result[auction_id] = entry[0]
        return result

    def prune_auction_id_map(self, max_age_seconds: float) -> int:
        """Remove entries older than max_age_seconds. Returns the number of entries pruned."""
        cutoff = time.monotonic() - max_age_seconds
        with self._auction_id_map_lock:
            stale = [k for k, (_, ts) in self._auction_id_map.items() if ts < cutoff]
            for k in stale:
                del self._auction_id_map[k]
        return len(stale)

    def fetch_bazaar_prices(self) -> dict[str, dict[str, int]]:
        self._logger.info("Starting Bazaar processing...")
        bazaar = requests.get(self.BAZAAR_URL, headers=self.HEADERS).json()
        prices: dict[str, dict[str, int]] = {"Coins": {"Buy Price": 1, "Sell Price": 1, "Weekly Volume": 0}}

        for product in bazaar["products"]:
            item_name = self._convert_name(product)
            qs = bazaar["products"][product]["quick_status"]
            prices[item_name] = {
                "Buy Price": qs["buyPrice"],
                "Sell Price": qs["sellPrice"],
                "Weekly Volume": qs["sellMovingWeek"],
            }

        self._logger.info("Bazaar processing complete.")
        return prices

    def _convert_name(self, bazaar_name: str) -> str:
        if bazaar_name == "DRILL_ENGINE":
            return "Drill Motor"
        if bazaar_name == "FUEL_TANK":
            return "Fuel Canister"
        if bazaar_name == "HAY_BLOCK":
            return "Hay Bale"
        if bazaar_name == "ENCHANTED_HAY_BLOCK":
            return "Enchanted Hay Bale"
        if bazaar_name == "ENCHANTED_COAL_BLOCK":
            return "Enchanted Block Of Coal"
        if bazaar_name == "GOBLIN_EGG_BLUE":
            return "Blue Goblin Egg"
        if bazaar_name == "GOBLIN_EGG_GREEN":
            return "Green Goblin Egg"
        if bazaar_name == "GOBLIN_EGG_RED":
            return "Red Goblin Egg"
        if bazaar_name == "GOBLIN_EGG_YELLOW":
            return "Yellow Goblin Egg"
        if bazaar_name == "MITHRIL_ORE":
            return "Mithril"

        converted_name = bazaar_name
        if bazaar_name.endswith("GEM"):
            converted_name = bazaar_name.replace("GEM", "GEMSTONE")

        return " ".join([part.capitalize() for part in converted_name.split(":")[0].split("_")])


class AHSalesTracker:
    ENDED_URL = "https://api.hypixel.net/v2/skyblock/auctions_ended"
    POLL_INTERVAL = 60

    def __init__(self, logger: logging.Logger, market: MarketPriceTracker, map_ttl: float = 1200.0) -> None:
        self._logger = logger
        self._market = market
        self._map_ttl = map_ttl

    def _poll_once(self) -> None:
        try:
            response = requests.get(self.ENDED_URL, timeout=10)
            response.raise_for_status()
            auctions = response.json().get("auctions", [])

            sold_ids = [a["auction_id"] for a in auctions if a.get("buyer") and a.get("bin")]
            resolved = self._market.resolve_and_remove(sold_ids)

            sales: dict[str, int] = {}
            for item_name in resolved.values():
                sales[item_name] = sales.get(item_name, 0) + 1

            pruned = self._market.prune_auction_id_map(self._map_ttl)
            if pruned:
                self._logger.info(f"Pruned {pruned} stale entries from auction ID map.")

            if sales:
                r = requests.post(f"{DB_API_URL}/ah-sales", json={"sales": sales}, timeout=10)
                r.raise_for_status()
                self._logger.info(f"Recorded {sum(sales.values())} AH sales across {len(sales)} items.")
        except Exception as e:
            self._logger.warning(f"AH sales poll failed: {e}")

    def run(self) -> None:
        while True:
            self._poll_once()
            time.sleep(self.POLL_INTERVAL)


class ProfitCalculator:
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self._market = MarketPriceTracker(logger)
        self._start_time = time.time()  # Track uptime for volume estimation

    @property
    def market(self) -> MarketPriceTracker:
        return self._market

    def calculate_profits(self, forge_info: dict[str, ForgeItemInfo]) -> tuple[list[ForgeProfit], int | None]:
        """Calculate profits for all forge items.
        Returns (profits_list, uptime_seconds).
        """
        auction_house_prices = self._market.fetch_auction_house_prices()
        bazaar_prices = self._market.fetch_bazaar_prices()

        # Calculate uptime and estimate if we have less than 7 days of data
        uptime_seconds = int(time.time() - self._start_time)
        is_estimated = uptime_seconds < 604800  # 7 days = 604800 seconds

        ah_weekly_sales: dict[str, int] = {}
        ah_volume_estimated: dict[str, bool] = {}

        try:
            response = requests.get(f"{DB_API_URL}/ah-sales", timeout=10)
            response.raise_for_status()
            ah_sales_data = response.json().get("sales", {})
            # Raw sales are just item_name -> total_quantity
            for item_name, total_quantity in ah_sales_data.items():
                if is_estimated:
                    # Extrapolate volume if we don't have 7 days yet
                    volume = int(total_quantity * 604800 / uptime_seconds)
                else:
                    volume = total_quantity
                ah_weekly_sales[item_name] = volume
                ah_volume_estimated[item_name] = is_estimated
        except Exception as e:
            self._logger.warning(f"Could not fetch AH weekly sales: {e}")
            ah_weekly_sales = {}
            ah_volume_estimated = {}

        self._logger.info("Starting final profit calculations...")
        items_profit: list[ForgeProfit] = []

        for item_name in forge_info.keys():
            item_cost = 0
            is_craftable = True
            is_sellable = True
            recipe_markets: dict[str, str] = {}

            for material in forge_info[item_name]["Recipe"].keys():
                material_bazaar_info = bazaar_prices.get(material)
                if material_bazaar_info:
                    material_price = material_bazaar_info.get("Buy Price", -1)
                    recipe_markets[material] = "Bazaar"
                else:
                    material_price = auction_house_prices.get(material, -1)
                    recipe_markets[material] = "AH"
                if material_price < 0:
                    is_craftable = False
                item_cost += forge_info[item_name]["Recipe"][material] * material_price

            item_bazaar_info = bazaar_prices.get(item_name)
            if item_bazaar_info:
                item_sell_price = item_bazaar_info.get("Sell Price", -1)
                weekly_volume = item_bazaar_info.get("Weekly Volume", 0)
                volume_source = "Bazaar"
                volume_estimated = False
            else:
                item_sell_price = auction_house_prices.get(item_name, -1)
                weekly_volume = ah_weekly_sales.get(item_name, 0)
                volume_source = "AH"
                volume_estimated = ah_volume_estimated.get(item_name, False)
            if item_sell_price < 0:
                is_sellable = False

            if is_craftable and is_sellable and item_sell_price > item_cost:
                items_profit.append(
                    {
                        "Rank": 0,
                        "Name": item_name,
                        "Cost": ceil(item_cost),
                        "Sell Value": ceil(item_sell_price),
                        "Profit": ceil(item_sell_price - item_cost),
                        "Duration": forge_info[item_name]["Duration"],
                        "Profit per Hour": ceil((item_sell_price - item_cost) / forge_info[item_name]["Duration"]),
                        "Weekly Volume": weekly_volume,
                        "Volume Estimated": volume_estimated,
                        "Selling Market": volume_source,
                        "Recipe Markets": recipe_markets,
                        "Recipe": forge_info[item_name]["Recipe"],
                        "Requirements": forge_info[item_name]["Requirements"],
                    }
                )

        return (
            [
                cast(ForgeProfit, {**item, "Rank": i + 1})
                for i, item in enumerate(sorted(items_profit, key=lambda x: x["Profit per Hour"], reverse=True))
            ],
            uptime_seconds,
        )


def main() -> None:
    formatter = logging.Formatter("%(asctime)s - calculator - %(levelname)s - %(message)s")

    logger = logging.getLogger("calculator")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    refresh_time = int(os.getenv("REFRESH_TIME", "120"))

    logger.info("Waiting for db-api...")
    wait_for_api(logger)
    logger.info("db-api ready. Checking for existing forge data...")

    while True:
        r = requests.get(f"{DB_API_URL}/forge-items", timeout=30)
        if r.json().get("items"):
            break
        logger.info("DB is empty, waiting for first scrape... retrying in 10s...")
        time.sleep(10)

    logger.info("Forge data available. Starting calculations.")
    calculator = ProfitCalculator(logger)

    sales_tracker = AHSalesTracker(logger, calculator.market, map_ttl=refresh_time * 10)
    t = threading.Thread(target=sales_tracker.run, daemon=True, name="ah-sales-tracker")
    t.start()
    logger.info("AH sales tracker thread started.")

    while True:
        response = requests.get(f"{DB_API_URL}/forge-items", timeout=30)
        response.raise_for_status()
        forge_info: dict[str, ForgeItemInfo] = {
            name: cast(ForgeItemInfo, info) for name, info in response.json()["items"].items()
        }
        if not forge_info:
            logger.info("No forge data in database yet, retrying in 10s...")
            time.sleep(10)
            continue

        logger.info(f"Loaded {len(forge_info)} forge items from DB. Calculating profits...")
        profits, uptime_seconds = calculator.calculate_profits(forge_info)

        try:
            requests.post(
                f"{WEB_URL}/results",
                json={
                    "profits": profits,
                    "calculated_at": datetime.now(timezone.utc).isoformat(),
                    "uptime_seconds": uptime_seconds,
                },
                timeout=10,
            )
            logger.info("Pushed results to web service.")
        except Exception as e:
            logger.warning(f"Could not push results to web service: {e}")

        logger.info(f"Done. Sleeping {refresh_time}s...")
        time.sleep(refresh_time)


if __name__ == "__main__":
    main()
