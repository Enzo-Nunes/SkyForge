import logging
import threading
import time

from calc_http import request_with_retry
from constants import DB_API_URL


class MarketPriceTracker:
    BAZAAR_URL = "https://api.hypixel.net/v2/skyblock/bazaar"
    AUCTION_HOUSE_URL = "https://api.hypixel.net/v2/skyblock/auctions"
    HEADERS = {"Content-Type": "application/json"}
    NAME_OVERRIDES = {
        "DRILL_ENGINE": "Drill Motor",
        "FUEL_TANK": "Fuel Canister",
        "HAY_BLOCK": "Hay Bale",
        "ENCHANTED_HAY_BLOCK": "Enchanted Hay Bale",
        "ENCHANTED_COAL_BLOCK": "Enchanted Block Of Coal",
        "GOBLIN_EGG_BLUE": "Blue Goblin Egg",
        "GOBLIN_EGG_GREEN": "Green Goblin Egg",
        "GOBLIN_EGG_RED": "Red Goblin Egg",
        "GOBLIN_EGG_YELLOW": "Yellow Goblin Egg",
        "MITHRIL_ORE": "Mithril",
    }
    SUFFIX_REPLACEMENTS = {"GEM": "GEMSTONE"}

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self._auction_id_map: dict[str, tuple[str, float]] = {}
        self._auction_id_map_lock = threading.Lock()

    def fetch_auction_house_prices(self) -> dict[str, int]:
        response = request_with_retry(self._logger, "GET", self.AUCTION_HOUSE_URL, headers=self.HEADERS)
        auction_house = response.json()
        pages = auction_house["totalPages"]
        items = auction_house["totalAuctions"]

        self._logger.info(f"Starting Auction House processing, {pages} pages found with a total of {items} auctions:")
        prices: dict[str, int] = {}
        new_id_map: dict[str, str] = {}

        for i in range(pages):
            try:
                page_response = request_with_retry(
                    self._logger,
                    "GET",
                    self.AUCTION_HOUSE_URL,
                    headers=self.HEADERS,
                    params={"page": i},
                    retries=2,
                )
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
        now = time.monotonic()
        with self._auction_id_map_lock:
            for uuid, name in new_entries.items():
                self._auction_id_map[uuid] = (name, now)

    def resolve_and_remove(self, auction_ids: list[str]) -> dict[str, str]:
        result: dict[str, str] = {}
        with self._auction_id_map_lock:
            for auction_id in auction_ids:
                entry = self._auction_id_map.pop(auction_id, None)
                if entry:
                    result[auction_id] = entry[0]
        return result

    def prune_auction_id_map(self, max_age_seconds: float) -> int:
        cutoff = time.monotonic() - max_age_seconds
        with self._auction_id_map_lock:
            stale = [k for k, (_, ts) in self._auction_id_map.items() if ts < cutoff]
            for k in stale:
                del self._auction_id_map[k]
        return len(stale)

    def fetch_bazaar_prices(self) -> dict[str, dict[str, int]]:
        self._logger.info("Starting Bazaar processing...")
        bazaar = request_with_retry(self._logger, "GET", self.BAZAAR_URL, headers=self.HEADERS).json()
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
        base_name = bazaar_name.split(":")[0]

        if bazaar_name in self.NAME_OVERRIDES:
            return self.NAME_OVERRIDES[bazaar_name]
        if base_name in self.NAME_OVERRIDES:
            return self.NAME_OVERRIDES[base_name]

        converted_name = base_name
        for suffix, replacement in self.SUFFIX_REPLACEMENTS.items():
            if converted_name.endswith(suffix):
                converted_name = f"{converted_name[: -len(suffix)]}{replacement}"
                break

        return " ".join(part.capitalize() for part in converted_name.split("_"))


class AHSalesTracker:
    ENDED_URL = "https://api.hypixel.net/v2/skyblock/auctions_ended"
    POLL_INTERVAL = 60

    def __init__(self, logger: logging.Logger, market: MarketPriceTracker, map_ttl: float = 1200.0) -> None:
        self._logger = logger
        self._market = market
        self._map_ttl = map_ttl

    def _poll_once(self) -> None:
        try:
            response = request_with_retry(self._logger, "GET", self.ENDED_URL, timeout=10)
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
                request_with_retry(self._logger, "POST", f"{DB_API_URL}/ah-sales", json={"sales": sales}, timeout=10)
                self._logger.info(f"Recorded {sum(sales.values())} AH sales across {len(sales)} items.")
        except Exception as e:
            self._logger.warning(f"AH sales poll failed: {e}")

    def run(self) -> None:
        while True:
            self._poll_once()
            time.sleep(self.POLL_INTERVAL)
