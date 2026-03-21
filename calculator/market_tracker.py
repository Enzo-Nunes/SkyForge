import logging
import threading
import time
import typing

from calc_http import request_with_retry
from calc_types import DB_API_URL

from common.types import ForgeItemInfo


class ForgeItemState:
    def __init__(self) -> None:
        self._forge_info: dict[str, ForgeItemInfo] = {}
        self._tracked_items: set[str] = set()
        self._sellable_items: set[str] = set()
        self._lock = threading.Lock()

    def update_from_forge_info(self, forge_info: dict[str, ForgeItemInfo]) -> None:
        tracked_items: set[str] = set(forge_info.keys())
        for item_info in forge_info.values():
            tracked_items.update(item_info["Recipe"].keys())

        sellable_items: set[str] = set(forge_info.keys())

        with self._lock:
            self._forge_info = dict(forge_info)
            self._tracked_items = tracked_items
            self._sellable_items = sellable_items

    def get_forge_info(self) -> dict[str, ForgeItemInfo]:
        with self._lock:
            return dict(self._forge_info)

    def get_tracked_items(self) -> set[str]:
        with self._lock:
            return set(self._tracked_items)

    def get_sellable_items(self) -> set[str]:
        with self._lock:
            return set(self._sellable_items)


class MarketPriceTracker:
    BAZAAR_URL = "https://api.hypixel.net/v2/skyblock/bazaar"
    AUCTION_HOUSE_URL = "https://api.hypixel.net/v2/skyblock/auctions"
    HEADERS = {
        "Content-Type": "application/json",
    }
    NAME_OVERRIDES = {
        "DRILL_ENGINE": "Drill Motor",
        "FUEL_TANK": "Fuel Canister",
        "GOBLIN_EGG_BLUE": "Blue Goblin Egg",
        "GOBLIN_EGG_GREEN": "Green Goblin Egg",
        "GOBLIN_EGG_RED": "Red Goblin Egg",
        "GOBLIN_EGG_YELLOW": "Yellow Goblin Egg",
        "MATCH_STICKS": "Match-Sticks",
    }
    SUFFIX_REPLACEMENTS = {
        "_GEM": "_GEMSTONE",
        "_ORE": "",
    }

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self._auction_id_map: dict[str, tuple[str, int, float]] = {}
        self._auction_id_map_lock = threading.Lock()
        self._snapshot_ready = threading.Event()

    def refresh_auction_house_state(self, tracked_items: set[str]) -> None:
        response = request_with_retry(self._logger, "GET", self.AUCTION_HOUSE_URL, headers=self.HEADERS)
        auction_house = response.json()
        pages = auction_house["totalPages"]
        items = auction_house["totalAuctions"]

        self._logger.info(f"Starting Auction House processing, {pages} pages found with a total of {items} auctions:")
        now_epoch = time.time()
        new_entries: dict[str, tuple[str, int, float]] = {}

        for i in range(pages):
            try:
                page_response = request_with_retry(
                    self._logger, "GET", self.AUCTION_HOUSE_URL, headers=self.HEADERS, params={"page": i}, retries=2
                )
                page = page_response.json()
            except Exception as e:
                self._logger.warning(f"Skipping AH page {i}: {e}")
                continue
            for auction in page.get("auctions", []):
                if not auction.get("bin"):
                    continue

                item_name = auction["item_name"]
                if item_name not in tracked_items:
                    continue

                auction_id = auction["uuid"]
                starting_bid = int(auction["starting_bid"])
                new_entries[auction_id] = (item_name, starting_bid, now_epoch)

        self._update_auction_state(new_entries)

        self._logger.info("Auction House processing complete.")

    def get_auction_house_prices_snapshot(self) -> dict[str, int]:
        prices: dict[str, int] = {}
        with self._auction_id_map_lock:
            for item_name, price, _ in self._auction_id_map.values():
                current = prices.get(item_name)
                if current is None or price < current:
                    prices[item_name] = price
        return prices

    def wait_for_snapshot(self, timeout: float | None = None) -> bool:
        return self._snapshot_ready.wait(timeout=timeout)

    def _update_auction_state(self, new_entries: dict[str, tuple[str, int, float]]) -> None:
        with self._auction_id_map_lock:
            self._auction_id_map = new_entries
            if new_entries:
                self._snapshot_ready.set()

    def resolve_and_remove(self, auction_ids: list[str]) -> dict[str, tuple[str, int]]:
        result: dict[str, tuple[str, int]] = {}
        with self._auction_id_map_lock:
            for auction_id in auction_ids:
                entry = self._auction_id_map.pop(auction_id, None)
                if entry:
                    result[auction_id] = (entry[0], entry[1])
        return result

    def get_sales_events(
        self, sellable_items: set[str], resolved: dict[str, tuple[str, int]]
    ) -> list[dict[str, str | int]]:

        sales_events: list[dict[str, typing.Any]] = []
        for auction_id, (item_name, price) in resolved.items():
            if item_name not in sellable_items:
                continue
            sales_events.append(
                {
                    "item_name": item_name,
                    "effective_price": int(price),
                    "auction_id": auction_id,
                }
            )
        return sales_events

    def prune_auction_state(self, max_stale_seconds: float) -> int:
        now_epoch = time.time()
        stale_cutoff = now_epoch - max_stale_seconds
        with self._auction_id_map_lock:
            stale = [k for k, (_, _, last_seen) in self._auction_id_map.items() if last_seen < stale_cutoff]
            for k in stale:
                del self._auction_id_map[k]
        return len(stale)

    def fetch_bazaar_prices(self, considered_items: set[str]) -> dict[str, dict[str, int]]:
        self._logger.info("Starting Bazaar processing...")
        bazaar = request_with_retry(self._logger, "GET", self.BAZAAR_URL, headers=self.HEADERS).json()
        prices: dict[str, dict[str, int]] = {
            "Coins": {
                "Buy Price": 1,
                "Sell Price": 1,
                "Weekly Volume": 0,
            },
        }

        for product in bazaar["products"]:
            item_name = self._convert_name(product)
            if item_name not in considered_items:
                continue

            qs = bazaar["products"][product]["quick_status"]
            prices[item_name] = {
                "Buy Price": int(round(qs["buyPrice"])),
                "Sell Price": int(round(qs["sellPrice"])),
                "Weekly Volume": int(round(qs["sellMovingWeek"])),
            }

        self._logger.info("Bazaar processing complete.")
        return prices

    def refresh_bazaar_snapshots(self, sellable_items: set[str]) -> None:
        bazaar_prices = self.fetch_bazaar_prices(sellable_items)

        snapshots = {item_name: info["Sell Price"] for item_name, info in bazaar_prices.items()}

        if snapshots:
            request_with_retry(
                self._logger,
                "POST",
                f"{DB_API_URL}/bazaar-snapshots",
                json={"snapshots": snapshots},
                timeout=10,
            )
            self._logger.info(f"Recorded Bazaar snapshots for {len(snapshots)} forge items.")

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

        return " ".join(part.capitalize() for part in converted_name.split("_")).strip()


class AHSalesTracker:
    ENDED_URL = "https://api.hypixel.net/v2/skyblock/auctions_ended"

    def __init__(
        self,
        logger: logging.Logger,
        market: MarketPriceTracker,
        item_state: ForgeItemState,
        poll_interval: int,
        state_stale_seconds: float,
    ) -> None:
        self._logger = logger
        self._market = market
        self._item_state = item_state
        self._poll_interval = poll_interval
        self._state_stale_seconds = state_stale_seconds

    def _poll_once(self, sellable_items: set[str]) -> None:
        try:
            response = request_with_retry(self._logger, "GET", self.ENDED_URL, timeout=10)
            auctions = response.json().get("auctions", [])
            sold_ids = [a["auction_id"] for a in auctions if a.get("buyer") and a.get("bin")]
            resolved = self._market.resolve_and_remove(sold_ids)
            sales_events = self._market.get_sales_events(sellable_items, resolved)

            pruned = self._market.prune_auction_state(self._state_stale_seconds)
            if pruned:
                self._logger.info(f"Pruned {pruned} stale entries from auction ID map.")

            if sales_events:
                request_with_retry(
                    self._logger,
                    "POST",
                    f"{DB_API_URL}/ah-sales",
                    json={"sales": sales_events},
                    timeout=10,
                )
                self._logger.info(f"Recorded {len(sales_events)} AH sales.")
        except Exception as e:
            self._logger.warning(f"AH sales poll failed: {e}")

    def run(self) -> None:
        while True:
            self._poll_once(self._item_state.get_sellable_items())
            time.sleep(self._poll_interval)


class MarketListingUpdater:
    def __init__(
        self, logger: logging.Logger, market: MarketPriceTracker, item_state: ForgeItemState, poll_interval: int
    ) -> None:
        self._logger = logger
        self._market = market
        self._item_state = item_state
        self._poll_interval = poll_interval

    def run(self) -> None:
        while True:
            self._market.refresh_auction_house_state(self._item_state.get_tracked_items())
            self._market.refresh_bazaar_snapshots(self._item_state.get_sellable_items())
            time.sleep(self._poll_interval)
