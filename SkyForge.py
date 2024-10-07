import json
import logging
import time

import bs4
import requests
import roman

HEART_OF_THE_MOUNTAIN_TIER = 4
GEMSTONE_COLLECTION = 4
TUNGSTEN_COLLECTION = 0
UMBER_COLLECTION = 0
GLACITE_COLLECTION = 0
HARD_STONE_COLLECTION = 0

# budget to invest per item (millions of coins)
BUDGET = 4

######################
# Auxiliar Functions #
######################

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
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
    logger.info("The top 10 Items for investing are as follows:")

    # Define the width for each column
    top_width = 8
    name_width = 24
    cost_width = 12
    sell_value_width = 12
    profit_width = 12
    duration_width = 12
    profit_per_hour_width = 20
    recipe_width = 32

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
    # Header with column names
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
        # Print main row with item info and the first recipe material
        profits_pretty += (
            f"{"| " + str(i + 1):<{top_width}}"
            f"{profit['Name']:<{name_width}}"
            f"{pretty_number(int(profit['Cost'])):<{cost_width}}"
            f"{pretty_number(int(profit['Sell Value'])):<{sell_value_width}}"
            f"{pretty_number(int(profit['Profit'])):<{profit_width}}"
            f"{str(round(profit['Duration'], 3)):<{duration_width}}"
            f"{pretty_number(int(profit['Profit per Hour'])):<{profit_per_hour_width}}"
            f"{list(profit['Recipe'].keys())[0] + ' x' + str(profit['Recipe'][list(profit['Recipe'].keys())[0]]):<{recipe_width}}|\n"
        )

        # Print any additional materials in the recipe (indented)
        for material in list(profit["Recipe"].keys())[1:]:
            profits_pretty += (
                f"{'|':<{top_width + name_width + cost_width + sell_value_width + profit_width + duration_width + profit_per_hour_width}}"
                f"{material + ' x' + str(profit['Recipe'][material]):<{recipe_width}}|\n"
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
    """
    Reads the forge page from the official wiki and parses it to the forge dictionary.

    :return: A dictionary containing the forge item details.
    """

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
        logger.info(f"Processing page {i}...")
        auction_house = requests.get(AUCTION_HOUSE_URL, headers=HEADERS, json={"page": i}).json()
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
            and item_cost < BUDGET * 10**6
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
    logger.info("Processing started...")
    the_forge = get_forge_info()
    logger.info("Forge data fetched. Calculating profits...")
    profits = calculate_forge_profits(the_forge)
    logger.info("All profits calculated. Exporting...")
    with open("final_profits.json", "w") as file:
        json.dump(profits, file, indent=4)
    logger.info("Data written to file. Processing complete, waiting 60s...")
    print(profits_str(profits[:10]))

    time.sleep(60)
