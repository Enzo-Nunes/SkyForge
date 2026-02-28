import logging
import os
import sys
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

    def fetch_auction_house_prices(self) -> dict[str, int]:
        auction_house = requests.get(self.AUCTION_HOUSE_URL, headers=self.HEADERS).json()
        pages = auction_house["totalPages"]
        items = auction_house["totalAuctions"]

        self._logger.info(f"Starting Auction House processing, {pages} pages found with a total of {items} auctions:")
        prices: dict[str, int] = {}

        for i in range(pages):
            page = requests.get(self.AUCTION_HOUSE_URL, headers=self.HEADERS, params={"page": i}).json()
            for auction in page.get("auctions", []):
                current_price = prices.get(auction["item_name"], -1)
                new_price = auction["starting_bid"]
                if auction["bin"] and (current_price == -1 or current_price > new_price):
                    prices[auction["item_name"]] = new_price

        self._logger.info("Auction House processing complete.")
        return prices

    def fetch_bazaar_prices(self) -> dict[str, dict[str, int]]:
        self._logger.info("Starting Bazaar processing...")
        bazaar = requests.get(self.BAZAAR_URL, headers=self.HEADERS).json()
        prices: dict[str, dict[str, int]] = {"Coins": {"Buy Price": 1, "Sell Price": 1}}

        for product in bazaar["products"]:
            item_name = self._convert_name(product)
            prices[item_name] = {
                "Buy Price": bazaar["products"][product]["quick_status"]["buyPrice"],
                "Sell Price": bazaar["products"][product]["quick_status"]["sellPrice"],
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

    def min_price(self, price1: int, price2: int) -> int:
        if price1 == -1:
            return price2
        if price2 == -1:
            return price1
        return min(price1, price2)

    def max_price(self, price1: int, price2: int) -> int:
        if price1 == -1:
            return price2
        if price2 == -1:
            return price1
        return max(price1, price2)


class ProfitCalculator:
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self._market = MarketPriceTracker(logger)

    def calculate_profits(self, forge_info: dict[str, ForgeItemInfo]) -> list[ForgeProfit]:
        auction_house_prices = self._market.fetch_auction_house_prices()
        bazaar_prices = self._market.fetch_bazaar_prices()

        self._logger.info("Starting final profit calculations...")
        items_profit: list[ForgeProfit] = []

        for item_name in forge_info.keys():
            item_cost = 0
            is_craftable = True
            is_sellable = True

            for material in forge_info[item_name]["Recipe"].keys():
                material_bazaar_info = bazaar_prices.get(material)
                material_bazaar_buy_price = material_bazaar_info.get("Buy Price", -1) if material_bazaar_info else -1
                material_min_price = self._market.min_price(
                    material_bazaar_buy_price, auction_house_prices.get(material, -1)
                )
                if material_min_price < 0:
                    is_craftable = False
                item_cost += forge_info[item_name]["Recipe"][material] * material_min_price

            item_bazaar_sell_info = bazaar_prices.get(item_name)
            item_bazaar_sell_price = item_bazaar_sell_info.get("Sell Price", -1) if item_bazaar_sell_info else -1
            item_sell_price = self._market.max_price(item_bazaar_sell_price, auction_house_prices.get(item_name, -1))
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
                        "Recipe": forge_info[item_name]["Recipe"],
                        "Requirements": forge_info[item_name]["Requirements"],
                    }
                )

        return [
            cast(ForgeProfit, {**item, "Rank": i + 1})
            for i, item in enumerate(sorted(items_profit, key=lambda x: x["Profit per Hour"], reverse=True))
        ]


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
        profits = calculator.calculate_profits(forge_info)

        try:
            requests.post(
                f"{WEB_URL}/results",
                json={
                    "profits": profits,
                    "calculated_at": datetime.now(timezone.utc).isoformat(),
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
