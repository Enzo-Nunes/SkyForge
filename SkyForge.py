import json
import logging
import time

import bs4
import requests
import roman

with open("SkyForgeConfigs.json", "r") as config_file:
    config = json.load(config_file)

HEART_OF_THE_MOUNTAIN_TIER = config.get("HEART_OF_THE_MOUNTAIN_TIER")
GEMSTONE_COLLECTION = config.get("GEMSTONE_COLLECTION")
TUNGSTEN_COLLECTION = config.get("TUNGSTEN_COLLECTION")
UMBER_COLLECTION = config.get("UMBER_COLLECTION")
GLACITE_COLLECTION = config.get("GLACITE_COLLECTION")
HARD_STONE_COLLECTION = config.get("HARD_STONE_COLLECTION")
BUDGET = config.get("BUDGET")
TABLE_LENGTH = config.get("TABLE_LENGTH")
REFRESH_TIME = config.get("REFRESH_TIME")

######################
# Auxiliar Functions #
######################

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(filename)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def is_char_upper(letter: str) -> bool:
    return ord("A") <= ord(letter) <= ord("Z")


def is_string_upper(string: str) -> bool:
    return all(is_char_upper(letter) for letter in string)


def time_to_hours(time: str) -> float:
    time_quantity, time_type = time.lstrip().split(" ")

    match time_type:
        case "days" | "day":
            return float(time_quantity) * 24
        case "hours" | "hour":
            return float(time_quantity)
        case "minutes" | "minute":
            return float(time_quantity) / 60
        case "seconds" | "second":
            return float(time_quantity) / 3600


def convert_name(bazaar_name: str) -> str:
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

    return " ".join([item_name.capitalize() for item_name in converted_name.split(":")[0].split("_")])


def min_price(price1: int, price2: int) -> int:
    if price1 == -1:
        return price2
    if price2 == -1:
        return price1
    return min(price1, price2)


def max_price(price1: int, price2: int) -> int:
    if price1 == -1:
        return price2
    if price2 == -1:
        return price1
    return max(price1, price2)


def is_unlocked(requirements: dict[str, int]) -> bool:
    return (
        HEART_OF_THE_MOUNTAIN_TIER >= requirements["Heart of the Mountain Tier"]
        and GEMSTONE_COLLECTION >= requirements["Gemstone Collection"]
        and TUNGSTEN_COLLECTION >= requirements["Tungsten Collection"]
        and UMBER_COLLECTION >= requirements["Umber Collection"]
        and GLACITE_COLLECTION >= requirements["Glacite Collection"]
        and HARD_STONE_COLLECTION >= requirements["Hard Stone Collection"]
    )


def pretty_number(number: int) -> str:
    number_list = list(str(number))
    for i in range(len(number_list) - 3, 0, -3):
        number_list.insert(i, ",")
    return "".join(number_list)


def profits_str(profits: list[dict[str, str | float | dict]]) -> str:
    logger.info(f"The top {TABLE_LENGTH} Items for investing are as follows:")

    spacing = 3

    top_list = [i + 1 for i in range(TABLE_LENGTH)]
    name_list = [profit["Name"] for profit in profits]
    cost_list = [pretty_number(int(profit["Cost"])) for profit in profits]
    sell_value_list = [pretty_number(int(profit["Sell Value"])) for profit in profits]
    profit_list = [pretty_number(int(profit["Profit"])) for profit in profits]
    duration_list = [str(round(profit["Duration"], 3)) for profit in profits]
    profit_per_hour_list = [pretty_number(int(profit["Profit per Hour"])) for profit in profits]
    recipe_list = [
        material + " x" + str(profit["Recipe"][material]) for profit in profits for material in profit["Recipe"]
    ]

    top_width = max(len("Top"), max(len(str(top)) for top in top_list)) + spacing + 2
    name_width = max(len("Item Name"), max(len(name) for name in name_list)) + spacing
    cost_width = max(len("Cost"), max(len(cost) for cost in cost_list)) + spacing
    sell_value_width = max(len("Sell Value"), max(len(sell_value) for sell_value in sell_value_list)) + spacing
    profit_width = max(len("Profit"), max(len(profit) for profit in profit_list)) + spacing
    duration_width = max(len("Duration"), max(len(duration) for duration in duration_list)) + spacing
    profit_per_hour_width = (
        max(len("Profit per Hour"), max(len(profit_per_hour) for profit_per_hour in profit_per_hour_list)) + spacing
    )
    recipe_width = max(len("Recipe"), max(len(recipe) for recipe in recipe_list)) + 2

    profits_pretty = (
        " "
        + "-"
        * (
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
        + "\n"
    )

    profits_pretty += (
        f"{"| Top":<{top_width}}"
        f"{"Item Name":<{name_width}}"
        f"{"Cost":<{cost_width}}"
        f"{"Sell Value":<{sell_value_width}}"
        f"{"Profit":<{profit_width}}"
        f"{"Duration":<{duration_width}}"
        f"{"Profit per Hour":<{profit_per_hour_width}}"
        f"{"Recipe":<{recipe_width}}|\n"
    )
    profits_pretty += (
        "|"
        + "-"
        * (
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
        + "|\n"
    )

    for i, profit in enumerate(profits):
        profits_pretty += (
            f"{"| " + str(i + 1):<{top_width}}"
            f"{profit["Name"]:<{name_width}}"
            f"{pretty_number(int(profit["Cost"])):<{cost_width}}"
            f"{pretty_number(int(profit["Sell Value"])):<{sell_value_width}}"
            f"{pretty_number(int(profit["Profit"])):<{profit_width}}"
            f"{str(round(profit["Duration"], 3)):<{duration_width}}"
            f"{pretty_number(int(profit["Profit per Hour"])):<{profit_per_hour_width}}"
            f"{str(profit["Recipe"][list(profit["Recipe"].keys())[0]]) + "x " + list(profit["Recipe"].keys())[0]:<{recipe_width}}|\n"
        )

        for material in list(profit["Recipe"].keys())[1:]:
            profits_pretty += (
                f"{"|":<{top_width + name_width + cost_width + sell_value_width + profit_width + duration_width + profit_per_hour_width}}"
                f"{str(profit["Recipe"][material]) + "x " + material:<{recipe_width}}|\n"
            )

        profits_pretty += (
            ("|" if i < len(profits) - 1 else " ")
            + "-"
            * (
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
            + ("|" if i < len(profits) - 1 else " ")
            + "\n"
        )

    return profits_pretty


###################
# Parse Functions #
###################


def parse_forge_page() -> list[dict[str, str | list]]:
    FORGE_URL = "https://wiki.hypixel.net/The_Forge"
    WIKI_INDEXES = range(1, 10)

    page = bs4.BeautifulSoup(requests.get(FORGE_URL).content, "html.parser")
    tables = page.find_all("table", {"class": "wikitable"})

    item_list = []
    for i in WIKI_INDEXES:
        rows = tables[i].find_all("tr")
        headers = [header.get_text(strip=True) for header in rows[0].find_all("th")]
        table_data = []
        for row in rows[1:]:
            columns = row.find_all("td")[1:]
            columns_text = [column.get_text() for column in columns]
            if len(columns_text) == len(headers):
                row_data = {}
                for i in range(len(headers)):
                    if headers[i] == "Recipe Tree":
                        row_data[headers[i]] = [
                            material.get_text()
                            for material in columns[3]
                            .find("div", {"class": "mw-hp-tree-container"})
                            .find("ul")
                            .find_all("li", recursive=False)
                        ]
                    else:
                        row_data[headers[i]] = columns_text[i]
                table_data.append(row_data)
        item_list.extend(table_data)
    return item_list


def parse_name(wiki_name: str) -> str:
    return wiki_name.split("  ")[0]


def parse_crafting_time(wiki_time: str) -> float:
    return sum(time_to_hours(time.strip()) for time in wiki_time.split(","))


def parse_recipe(wiki_recipe: list[str]) -> dict[str, int]:
    recipe = {}
    for item_chain in wiki_recipe:
        quantity, item = item_chain.split("[]")[0].split("  ")
        recipe[item.strip()] = int(quantity.replace(",", ""))

    return recipe


def parse_requirements(wiki_requirements: str) -> dict[str, int]:
    requirements_split = [requirement.strip() for requirement in wiki_requirements.split("  ")]
    requirements_split = [
        requirement
        for requirement in requirements_split
        if requirement != "Donating a"
        and "Fossil" not in requirement
        and requirement != "Dr. Stone"
        and requirement != "Riding a Minecart to the Dwarven Base Camp"
        and requirement != "Talk to"
        and requirement != "Dulin"
    ]

    requirements = {
        "Heart of the Mountain Tier": 0,
        "Gemstone Collection": 0,
        "Tungsten Collection": 0,
        "Umber Collection": 0,
        "Glacite Collection": 0,
        "Hard Stone Collection": 0,
    }

    for requirement in requirements_split:
        requirement_split = requirement.split(" ")

        requirement_type = " ".join(requirement_split[:-1])
        if "Donating" in requirement_type:
            continue
        if requirement_type not in requirements.keys():
            raise ValueError(f"New requirement detected: {requirement_type}")

        requirement_level = requirement_split[-1]
        requirements[requirement_type] = (
            int(requirement_level) if requirement_level.isnumeric() else roman.fromRoman(requirement_level)
        )

    return requirements


##################
# Main Functions #
##################


def get_forge_info() -> dict[str, dict[str, int | float | dict[str, int]]]:
    the_forge = {}
    item_list = parse_forge_page()
    for forge_item in item_list:
        the_forge[parse_name(forge_item["Name & Rarity"])] = {
            "Duration": parse_crafting_time(forge_item["Duration"]),
            "Recipe": parse_recipe(forge_item["Recipe Tree"]),
            "Requirements": parse_requirements(forge_item["Requirements"]),
        }

    return the_forge


def calculate_forge_profits(
    the_forge: dict[str, dict[str, int | float | dict[str, int]]],
) -> list[dict[str, str | float | dict]]:
    BAZAAR_URL = "https://api.hypixel.net/v2/skyblock/bazaar"
    AUCTION_HOUSE_URL = "https://api.hypixel.net/v2/skyblock/auctions"
    HEADERS = {"Content-Type": "application/json"}

    auction_house = requests.get(AUCTION_HOUSE_URL, headers=HEADERS).json()
    pages = auction_house["totalPages"]

    logger.info(f"Starting Auction House processing, {pages} pages found:")
    auction_house_price = {}
    for i in range(pages):
        logger.info(f"Processing Auction House page {i + 1}/{pages}...")
        auction_house = requests.get(AUCTION_HOUSE_URL, headers=HEADERS, params={"page": i}).json()
        for auction in auction_house["auctions"]:
            current_price = auction_house_price.get(auction["item_name"], -1)
            new_price = auction["starting_bid"]
            if auction["bin"] and (current_price == -1 or current_price > new_price):
                auction_house_price[auction["item_name"]] = new_price

    logger.info("Auction House processing complete. Starting Bazaar processing...")
    bazaar = requests.get(BAZAAR_URL, headers=HEADERS).json()
    bazaar_price = {"Coins": {"Buy Price": 1, "Sell Price": 1}}
    products = bazaar["products"]
    for product in products:
        item_name = convert_name(product)
        bazaar_price[item_name] = {
            "Buy Price": products[product]["quick_status"]["buyPrice"],
            "Sell Price": products[product]["quick_status"]["sellPrice"],
        }

    logger.info("Bazaar processing complete. Starting final profit calculations...")
    items_profit = []
    for item_name in the_forge.keys():
        item_cost = 0
        is_craftable = True
        is_sellabe = True
        for material in the_forge[item_name]["Recipe"].keys():
            material_bazaar_buy_price = bazaar_price.get(material, -1)
            if material_bazaar_buy_price != -1:
                material_bazaar_buy_price = material_bazaar_buy_price.get("Buy Price", -1)
            material_min_price = min_price(material_bazaar_buy_price, auction_house_price.get(material, -1))
            if material_min_price < 0:
                is_craftable = False
            item_cost += the_forge[item_name]["Recipe"][material] * material_min_price

        item_bazaar_sell_price = bazaar_price.get(item_name, -1)
        if item_bazaar_sell_price != -1:
            item_bazaar_sell_price = item_bazaar_sell_price.get("Sell Price", -1)
        item_sell_price = max_price(item_bazaar_sell_price, auction_house_price.get(item_name, -1))
        if item_sell_price < 0:
            is_sellabe = False

        if (
            is_craftable
            and is_sellabe
            and item_sell_price > item_cost
            and item_cost <= BUDGET * 10**6
            and is_unlocked(the_forge[item_name]["Requirements"])
        ):
            items_profit.append(
                {
                    "Name": item_name,
                    "Cost": item_cost,
                    "Sell Value": item_sell_price,
                    "Profit": item_sell_price - item_cost,
                    "Duration": the_forge[item_name]["Duration"],
                    "Profit per Hour": (item_sell_price - item_cost) / the_forge[item_name]["Duration"],
                    "Recipe": the_forge[item_name]["Recipe"],
                }
            )

    items_profit.sort(key=lambda x: x["Profit per Hour"], reverse=True)
    return items_profit


while True:
    with open("SkyForgeConfigs.json", "r") as config_file:
        config = json.load(config_file)

    HEART_OF_THE_MOUNTAIN_TIER = config.get("HEART_OF_THE_MOUNTAIN_TIER")
    GEMSTONE_COLLECTION = config.get("GEMSTONE_COLLECTION")
    TUNGSTEN_COLLECTION = config.get("TUNGSTEN_COLLECTION")
    UMBER_COLLECTION = config.get("UMBER_COLLECTION")
    GLACITE_COLLECTION = config.get("GLACITE_COLLECTION")
    HARD_STONE_COLLECTION = config.get("HARD_STONE_COLLECTION")
    BUDGET = config.get("BUDGET")
    TABLE_LENGTH = config.get("TABLE_LENGTH")
    REFRESH_TIME = config.get("REFRESH_TIME")

    logger.info("Processing started...")
    the_forge = get_forge_info()
    logger.info("Forge data fetched. Calculating profits...")
    profits = calculate_forge_profits(the_forge)
    logger.info("All profits calculated. Exporting...")
    with open("best_forge_items.json", "w") as file:
        json.dump(profits, file, indent=4)
    logger.info(f"Data written to file. Processing complete, waiting {REFRESH_TIME} seconds...")
    print(profits_str(profits[:TABLE_LENGTH]))

    time.sleep(REFRESH_TIME)
