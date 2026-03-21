import logging
import sys
import threading
import time

from market_tracker import AHSalesTracker, ForgeItemState, MarketListingUpdater, MarketPriceTracker
from profit_calculator import ProfitCalculator
from runtime import CalculatorRuntime


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

    item_state = ForgeItemState()
    item_state.update_from_forge_info(runtime.fetch_forge_items())

    logger.info("Forge data available. Starting calculations.")
    market = MarketPriceTracker(logger)
    calculator = ProfitCalculator(logger, market, item_state)

    listing_poller = MarketListingUpdater(
        logger,
        market,
        item_state,
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
        item_state,
        poll_interval=runtime.listing_refresh_time,
        state_stale_seconds=runtime.auction_state_stale_seconds,
    )
    sales_thread = threading.Thread(target=sales_tracker.run, daemon=True, name="ah-sales-tracker")
    sales_thread.start()
    logger.info("AH sales tracker thread started.")

    while True:
        item_state.update_from_forge_info(runtime.fetch_forge_items())
        forge_info = item_state.get_forge_info()

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
