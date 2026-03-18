import logging
import sys
import threading
import time

from market_tracker import AHSalesTracker, MarketPriceTracker
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

    logger.info("Forge data available. Starting calculations.")
    market = MarketPriceTracker(logger)
    calculator = ProfitCalculator(logger, market)

    sales_tracker = AHSalesTracker(logger, market, map_ttl=runtime.refresh_time * 10)
    t = threading.Thread(target=sales_tracker.run, daemon=True, name="ah-sales-tracker")
    t.start()
    logger.info("AH sales tracker thread started.")

    while True:
        forge_info = runtime.fetch_forge_items()
        if not forge_info:
            logger.info("No forge data in database yet, retrying in 10s...")
            time.sleep(10)
            continue

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
