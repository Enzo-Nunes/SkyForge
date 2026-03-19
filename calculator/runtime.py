import logging
import os
import time
import typing
from datetime import datetime, timezone

from calc_http import request_with_retry
from calc_types import ForgeProfit
from constants import DB_API_URL, WEB_URL

from common.types import ForgeItemInfo


class CalculatorRuntime:
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self.refresh_time = int(os.getenv("REFRESH_TIME", "120"))
        self.listing_refresh_time = int(os.getenv("LISTING_REFRESH_TIME", "45"))
        self.ended_auctions_refresh_time = int(os.getenv("ENDED_AUCTIONS_REFRESH_TIME", "60"))
        self.auction_state_stale_seconds = float(os.getenv("AH_STATE_STALE_SECONDS", "900"))
        self.auction_state_end_grace_seconds = float(os.getenv("AH_STATE_END_GRACE_SECONDS", "180"))

    def wait_for_db_api(self, retries: int = 10, delay: int = 5) -> None:
        for attempt in range(retries):
            try:
                request_with_retry(self._logger, "GET", f"{DB_API_URL}/health", timeout=10, retries=1)
                return
            except Exception:
                if attempt < retries - 1:
                    self._logger.info(f"db-api not ready (attempt {attempt + 1}/{retries}), retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    raise RuntimeError(f"Could not connect to db-api after {retries} attempts")

    def wait_for_forge_data(self) -> None:
        while True:
            response = request_with_retry(self._logger, "GET", f"{DB_API_URL}/forge-items", timeout=30)
            if response.json().get("items"):
                return
            self._logger.info("DB is empty, waiting for forge data... retrying in 10s...")
            time.sleep(10)

    def fetch_forge_items(self) -> dict[str, ForgeItemInfo]:
        response = request_with_retry(self._logger, "GET", f"{DB_API_URL}/forge-items", timeout=30)
        return {name: typing.cast(ForgeItemInfo, info) for name, info in response.json()["items"].items()}

    def publish_results(self, profits: list[ForgeProfit], uptime_seconds: int | None) -> None:
        request_with_retry(
            self._logger,
            "POST",
            f"{WEB_URL}/results",
            json={
                "profits": profits,
                "calculated_at": datetime.now(timezone.utc).isoformat(),
                "uptime_seconds": uptime_seconds,
            },
            timeout=10,
        )
