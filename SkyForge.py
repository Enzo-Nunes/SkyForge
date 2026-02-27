import json
import logging
import sys
import time
from typing import TypedDict, cast

import bs4
import requests
import roman

##############
# TypedDicts #
##############

ForgePageItem = TypedDict(
    "ForgePageItem",
    {
        "Name & Rarity": str,
        "Duration": str,
        "Recipe Tree": list[str],
        "Requirements": str,
    },
)

ForgeItemInfo = TypedDict(
    "ForgeItemInfo",
    {
        "Duration": float,
        "Recipe": dict[str, int],
        "Requirements": dict[str, int],
    },
)

ForgeProfit = TypedDict(
    "ForgeProfit",
    {
        "Rank": int,
        "Name": str,
        "Cost": int,
        "Sell Value": int,
        "Profit": int,
        "Duration": float,
        "Profit per Hour": float,
        "Recipe": dict[str, int],
    },
)

###########
# Classes #
###########


class SkyForgeConfig:
    def __init__(self, config_path: str = "SkyForgeConfigs.json") -> None:
        self.config_path = config_path
        self.heart_of_the_mountain_tier: int = 0
        self.gemstone_collection: int = 0
        self.tungsten_collection: int = 0
        self.umber_collection: int = 0
        self.glacite_collection: int = 0
        self.hard_stone_collection: int = 0
        self.budget: int = 0
        self.table_length: int = 0
        self.refresh_time: int = 0

    def load(self) -> None:
        with open(self.config_path, "r") as config_file:
            raw = dict(json.load(config_file))

        self.heart_of_the_mountain_tier = int(raw.get("Heart of the Mountain Tier", 0))
        self.gemstone_collection = int(raw.get("Gemstone Collection", 0))
        self.tungsten_collection = int(raw.get("Tungsten Collection", 0))
        self.umber_collection = int(raw.get("Umber Collection", 0))
        self.glacite_collection = int(raw.get("Glacite Collection", 0))
        self.hard_stone_collection = int(raw.get("Hard Stone Collection", 0))
        self.budget = int(raw.get("Budget (coins per item)", 0))
        self.table_length = int(raw.get("Table Length (lines)", 0))
        self.refresh_time = int(raw.get("Refresh Time (seconds)", 0))

    def is_unlocked(self, requirements: dict[str, int]) -> bool:
        return (
            self.heart_of_the_mountain_tier >= requirements.get("Heart of the Mountain Tier", 0)
            and self.gemstone_collection >= requirements.get("Gemstone Collection", 0)
            and self.tungsten_collection >= requirements.get("Tungsten Collection", 0)
            and self.umber_collection >= requirements.get("Umber Collection", 0)
            and self.glacite_collection >= requirements.get("Glacite Collection", 0)
            and self.hard_stone_collection >= requirements.get("Hard Stone Collection", 0)
        )


class ForgeWikiParser:
    FORGE_URL = "https://wiki.hypixel.net/The_Forge"
    WIKI_INDEXES = range(1, 10)

    def get_forge_info(self) -> dict[str, ForgeItemInfo]:
        return {
            self._parse_name(forge_item["Name & Rarity"]): {
                "Duration": self._parse_crafting_time(forge_item["Duration"]),
                "Recipe": self._parse_recipe(forge_item["Recipe Tree"]),
                "Requirements": self._parse_requirements(forge_item["Requirements"]),
            }
            for forge_item in self._parse_page()
        }

    def _parse_page(self) -> list[ForgePageItem]:
        page = requests.get(
            self.FORGE_URL,
            headers={  # I'm a browser, let me through!
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            },
        )

        tables = bs4.BeautifulSoup(
            page.content,
            "html.parser",
        ).find_all("table", {"class": "wikitable"})

        item_list: list[ForgePageItem] = []
        for i in self.WIKI_INDEXES:
            rows = tables[i].find_all("tr")
            headers = [header.get_text(strip=True) for header in rows[0].find_all("th")]
            table_data: list[ForgePageItem] = []
            for row in rows[1:]:
                columns = row.find_all("td")[1:]
                columns_text = [column.get_text() for column in columns]
                if len(columns_text) == len(headers):
                    row_data: ForgePageItem = cast(ForgePageItem, {})
                    for j in range(len(headers)):
                        if headers[j] == "Recipe Tree":
                            tree_container = cast(bs4.Tag, columns[3].find("div", {"class": "mw-hp-tree-container"}))
                            ul_element = cast(bs4.Tag, tree_container.find("ul"))
                            row_data[headers[j]] = [
                                material.get_text() for material in ul_element.find_all("li", recursive=False)
                            ]
                        else:
                            row_data[headers[j]] = columns_text[j]
                    table_data.append(row_data)
            item_list.extend(table_data)
        return item_list

    def _parse_name(self, wiki_name: str) -> str:
        return wiki_name.split("  ")[0]

    def _parse_crafting_time(self, wiki_time: str) -> float:
        return sum(self._time_to_hours(time_str.strip()) for time_str in wiki_time.split(","))

    def _time_to_hours(self, time_str: str) -> float:
        time_quantity, time_type = time_str.lstrip().split(" ")

        match time_type:
            case "days" | "day":
                return float(time_quantity) * 24
            case "hours" | "hour":
                return float(time_quantity)
            case "minutes" | "minute":
                return float(time_quantity) / 60
            case "seconds" | "second":
                return float(time_quantity) / 3600
            case _:
                raise ValueError(f"Unknown time type: {time_type}")

    def _parse_recipe(self, wiki_recipe: list[str]) -> dict[str, int]:
        return {
            (ingredient_info := item_chain.split("[]")[0].split("  "))[1].strip(): int(
                ingredient_info[0].replace(",", "")
            )
            for item_chain in wiki_recipe
        }

    def _parse_requirements(self, wiki_requirements: str) -> dict[str, int]:
        return {
            " ".join((requirement_split := requirement.split(" "))[:-1]): (
                int(requirement_split[-1])
                if requirement_split[-1].isnumeric()
                else roman.fromRoman(requirement_split[-1])
            )
            for requirement in map(str.strip, wiki_requirements.split("  "))
            if "Donating" not in requirement
            and "Fossil" not in requirement
            and requirement != "Dr. Stone"
            and requirement != "Riding a Minecart to the Dwarven Base Camp"
            and requirement != "Talk to"
            and requirement != "Dulin"
        }


class MarketPriceTracker:
    BAZAAR_URL = "https://api.hypixel.net/v2/skyblock/bazaar"
    AUCTION_HOUSE_URL = "https://api.hypixel.net/v2/skyblock/auctions"
    HEADERS = {"Content-Type": "application/json"}

    def __init__(self, logger: logging.Logger, progress_logger: logging.Logger) -> None:
        self._logger = logger
        self._progress_logger = progress_logger

    def fetch_auction_house_prices(self) -> dict[str, int]:
        auction_house = requests.get(self.AUCTION_HOUSE_URL, headers=self.HEADERS).json()
        pages = auction_house["totalPages"]
        items = auction_house["totalAuctions"]

        self._logger.info(f"Starting Auction House processing, {pages} pages found with a total of {items} auctions:")
        prices: dict[str, int] = {}

        for i in range(pages):
            self._progress_logger.info(
                f"Processing Auction House page {i + 1}/{pages}, Total progress: {round((i + 1) / pages * 100)}%"
            )
            page = requests.get(self.AUCTION_HOUSE_URL, headers=self.HEADERS, params={"page": i}).json()
            for auction in page["auctions"]:
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


class SkyForge:
    def __init__(self) -> None:
        self.config = SkyForgeConfig()
        self._parser = ForgeWikiParser()

        formatter = logging.Formatter("%(asctime)s - %(filename)s - %(levelname)s - %(message)s")

        self._logger = logging.getLogger("SkyForge Info Logger")
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)
        self._logger.setLevel(logging.INFO)

        self._progress_logger = logging.getLogger("Progress Logger")
        progress_handler = logging.StreamHandler(sys.stdout)
        progress_handler.terminator = "\r"
        progress_handler.setFormatter(formatter)
        self._progress_logger.addHandler(progress_handler)
        self._progress_logger.setLevel(logging.INFO)

        self._market = MarketPriceTracker(self._logger, self._progress_logger)

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

            if (
                is_craftable
                and is_sellable
                and item_sell_price > item_cost
                and (self.config.budget == -1 or item_cost <= self.config.budget)
                and self.config.is_unlocked(forge_info[item_name]["Requirements"])
            ):
                items_profit.append(
                    {
                        "Rank": 0,
                        "Name": item_name,
                        "Cost": item_cost,
                        "Sell Value": item_sell_price,
                        "Profit": item_sell_price - item_cost,
                        "Duration": forge_info[item_name]["Duration"],
                        "Profit per Hour": (item_sell_price - item_cost) / forge_info[item_name]["Duration"],
                        "Recipe": forge_info[item_name]["Recipe"],
                    }
                )

        return [
            cast(ForgeProfit, {**item, "Rank": i + 1})
            for i, item in enumerate(sorted(items_profit, key=lambda x: x["Profit per Hour"], reverse=True))
        ]

    def profits_str(self, profits_list: list[ForgeProfit]) -> str:
        self._logger.info(f"The top {self.config.table_length} Items for investing are as follows:")

        spacing = 3

        top_list = [i + 1 for i in range(self.config.table_length)]
        name_list = [profit["Name"] for profit in profits_list]
        cost_list = [self._pretty_number(int(profit["Cost"])) for profit in profits_list]
        sell_value_list = [self._pretty_number(int(profit["Sell Value"])) for profit in profits_list]
        profit_list = [self._pretty_number(int(profit["Profit"])) for profit in profits_list]
        duration_list = [str(round(profit["Duration"], 3)) for profit in profits_list]
        profit_per_hour_list = [self._pretty_number(int(profit["Profit per Hour"])) for profit in profits_list]
        recipe_list = [
            material + " x" + str(profit["Recipe"][material])
            for profit in profits_list
            for material in profit["Recipe"]
        ]

        top_width = max(len("Top"), max(len(str(top)) for top in top_list)) + spacing + 2
        name_width = max(len("Item Name"), max(len(name) for name in name_list)) + spacing
        cost_width = max(len("Cost"), max(len(cost) for cost in cost_list)) + spacing
        sell_value_width = max(len("Sell Value"), max(len(sell_value) for sell_value in sell_value_list)) + spacing
        profit_width = max(len("Profit"), max(len(profit) for profit in profit_list)) + spacing
        duration_width = max(len("Duration"), max(len(duration) for duration in duration_list)) + spacing
        profit_per_hour_width = max(len("Profit per Hour"), max(len(pph) for pph in profit_per_hour_list)) + spacing
        recipe_width = max(len("Recipe"), max(len(recipe) for recipe in recipe_list)) + 2

        divider_width = (
            top_width
            + name_width
            + cost_width
            + sell_value_width
            + profit_width
            + duration_width
            + profit_per_hour_width
            + recipe_width
            - 1
        )

        profits_pretty = " " + "-" * divider_width + "\n"
        profits_pretty += (
            f"{'| Top':<{top_width}}"
            f"{'Item Name':<{name_width}}"
            f"{'Cost':<{cost_width}}"
            f"{'Sell Value':<{sell_value_width}}"
            f"{'Profit':<{profit_width}}"
            f"{'Duration':<{duration_width}}"
            f"{'Profit per Hour':<{profit_per_hour_width}}"
            f"{'Recipe':<{recipe_width}}|\n"
        )
        profits_pretty += "|" + "-" * divider_width + "|\n"

        for i, profit in enumerate(profits_list):
            profits_pretty += (
                f"{'| ' + str(i + 1):<{top_width}}"
                f"{profit['Name']:<{name_width}}"
                f"{self._pretty_number(int(profit['Cost'])):<{cost_width}}"
                f"{self._pretty_number(int(profit['Sell Value'])):<{sell_value_width}}"
                f"{self._pretty_number(int(profit['Profit'])):<{profit_width}}"
                f"{str(round(profit['Duration'], 3)):<{duration_width}}"
                f"{self._pretty_number(int(profit['Profit per Hour'])):<{profit_per_hour_width}}"
                f"{str(profit['Recipe'][list(profit['Recipe'].keys())[0]]) + 'x ' + list(profit['Recipe'].keys())[0]:<{recipe_width}}|\n"
            )

            for material in list(profit["Recipe"].keys())[1:]:
                profits_pretty += (
                    f"{'|':<{top_width + name_width + cost_width + sell_value_width + profit_width + duration_width + profit_per_hour_width}}"
                    f"{str(profit['Recipe'][material]) + 'x ' + material:<{recipe_width}}|\n"
                )

            sep = "|" if i < len(profits_list) - 1 else " "
            profits_pretty += sep + "-" * divider_width + sep + "\n"

        return profits_pretty

    def run(self) -> None:
        while True:
            self.config.load()

            self._logger.info("Processing started...")
            forge_info = self._parser.get_forge_info()

            self._logger.info("Forge data fetched. Calculating profits...")
            profits = self.calculate_profits(forge_info)

            self._logger.info("All profits calculated. Exporting...")
            with open("best_forge_items.json", "w") as file:
                json.dump(profits, file, indent=4)

            self._logger.info(
                f"Data written to file. Processing complete, waiting {self.config.refresh_time} seconds..."
            )
            print(self.profits_str(profits[: self.config.table_length]))

            time.sleep(self.config.refresh_time)

    def _pretty_number(self, number: int) -> str:
        number_list = list(str(number))
        for i in range(len(number_list) - 3, 0, -3):
            number_list.insert(i, ",")
        return "".join(number_list)


########
# Main #
########

if __name__ == "__main__":
    SkyForge().run()
