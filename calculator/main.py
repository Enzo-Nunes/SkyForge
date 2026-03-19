import logging
import sys
import threading
import time

from market_tracker import AHListingPoller, AHSalesTracker, MarketPriceTracker
from profit_calculator import ProfitCalculator
from runtime import CalculatorRuntime

from common.types import ForgeItemInfo


def build_tracked_items(forge_info: dict[str, ForgeItemInfo]) -> set[str]:
    tracked: set[str] = set(forge_info.keys())
    for item_info in forge_info.values():
        tracked.update(item_info["Recipe"].keys())
    return tracked


def build_sellable_items(forge_info: dict[str, ForgeItemInfo]) -> set[str]:
    return set(forge_info.keys())


def main() -> None:
    formatter = logging.Formatter("%(asctime)s - calculator - %(levelname)s - %(message)s")

    logger = logging.getLogger("calculator")
    logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    runtime = CalculatorRuntime(logger)

    logger.info("Waiting for db-api...")
    runtime.wait_for_db_api()
    logger.info("db-api ready. Checking for existing forge data...")
    runtime.wait_for_forge_data()

    logger.info("Forge data available. Starting calculations.")
    market = MarketPriceTracker(logger)
    calculator = ProfitCalculator(logger, market)

    initial_forge_info = runtime.fetch_forge_items()
    tracked_items: set[str] = build_tracked_items(initial_forge_info)
    sellable_items: set[str] = build_sellable_items(initial_forge_info)

    listing_poller = AHListingPoller(
        logger,
        market,
        get_tracked_items=lambda: tracked_items,
        poll_interval=runtime.listing_refresh_time,
    )
    listing_thread = threading.Thread(target=listing_poller.run, daemon=True, name="ah-listing-poller")
    listing_thread.start()
    logger.info("AH listing poller thread started.")

    logger.info("Waiting for first AH listing snapshot from poller...")
    while not market.wait_for_snapshot(timeout=runtime.listing_refresh_time):
        logger.info("Still waiting for first AH listing snapshot...")
    logger.info("Initial AH listing snapshot is ready.")

    sales_tracker = AHSalesTracker(
        logger,
        market,
        get_sellable_items=lambda: sellable_items,
        poll_interval=runtime.ended_auctions_refresh_time,
        state_stale_seconds=runtime.auction_state_stale_seconds,
        state_end_grace_seconds=runtime.auction_state_end_grace_seconds,
    )
    sales_thread = threading.Thread(target=sales_tracker.run, daemon=True, name="ah-sales-tracker")
    sales_thread.start()
    logger.info("AH sales tracker thread started.")

    while True:
        forge_info = runtime.fetch_forge_items()
        if not forge_info:
            logger.info("No forge data in database yet, retrying in 10s...")
            time.sleep(10)
            continue

        tracked_items = build_tracked_items(forge_info)
        sellable_items = build_sellable_items(forge_info)

        logger.info(f"Loaded {len(forge_info)} forge items from DB. Calculating profits...")
        profits, uptime_seconds = calculator.calculate_profits(forge_info)

        try:
            runtime.publish_results(profits, uptime_seconds)
            logger.info("Pushed results to web service.")
        except Exception as e:
            logger.warning(f"Could not push results to web service: {e}")

        logger.info(f"Done. Sleeping {runtime.refresh_time}s...")
        time.sleep(runtime.refresh_time)


if __name__ == "__main__":
    main()
