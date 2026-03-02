import logging
import os
import sys
import time
from typing import cast

import bs4
import requests
import roman
from curl_cffi import requests as cffi_requests

from common.types import ForgeItemInfo, ForgePageItem

DB_API_URL = "http://db-api:5000"


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


class ForgeWikiParser:
    FORGE_URL = "https://wiki.hypixel.net/The_Forge"
    WIKI_INDEXES = range(1, 10)

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

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
        response = cffi_requests.get(self.FORGE_URL, impersonate="firefox")
        response.raise_for_status()
        self._logger.info("Fetched forge data from wiki.")

        tables = bs4.BeautifulSoup(response.content, "html.parser").find_all("table", {"class": "wikitable"})

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


def main() -> None:
    formatter = logging.Formatter("%(asctime)s - scraper - %(levelname)s - %(message)s")
    logger = logging.getLogger("scraper")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    wiki_scrape_interval = int(os.getenv("WIKI_SCRAPE_INTERVAL", "3600"))
    parser = ForgeWikiParser(logger)

    logger.info("Waiting for db-api...")
    wait_for_api(logger)
    logger.info("db-api ready.")

    while True:
        logger.info("Fetching forge data...")
        try:
            forge_info = parser.get_forge_info()
            response = requests.put(f"{DB_API_URL}/forge-items", json={"items": forge_info}, timeout=30)
            response.raise_for_status()
            logger.info(f"Upserted {len(forge_info)} forge items.")
        except Exception as e:
            logger.error(f"Failed to fetch/store forge data: {e}")

        logger.info(f"Sleeping {wiki_scrape_interval}s...")
        time.sleep(wiki_scrape_interval)


if __name__ == "__main__":
    main()
