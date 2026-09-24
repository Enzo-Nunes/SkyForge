import logging
import os
import time
import typing
from datetime import datetime, timezone
from pathlib import Path

from calc_http import request_with_retry
from calc_types import DB_API_URL, ForgeProfit

from common.types import ForgeItemInfo

WEB_URL = "http://web:8000"
RESULTS_TOKEN_FILE = Path(os.getenv("RESULTS_TOKEN_FILE", "/run/skyforge/results_token"))
# Hypixel's auctions_ended endpoint only covers the last 60 seconds, so slower polling misses sales.
MAX_LISTING_REFRESH_TIME = 59


class CalculatorRuntime:
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self.refresh_time = int(os.getenv("REFRESH_TIME", "120"))
        self.listing_refresh_time = int(os.getenv("LISTING_REFRESH_TIME", "45"))
        if not 0 < self.listing_refresh_time <= MAX_LISTING_REFRESH_TIME:
            self._logger.warning(
                f"LISTING_REFRESH_TIME={self.listing_refresh_time} is outside 1-{MAX_LISTING_REFRESH_TIME}s; "
                f"using {MAX_LISTING_REFRESH_TIME}s."
            )
            self.listing_refresh_time = MAX_LISTING_REFRESH_TIME
        self.auction_state_stale_seconds = float(os.getenv("AH_STATE_STALE_SECONDS", "900"))

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
        # Read on every publish: the web service writes a fresh token each time it starts.
        token = RESULTS_TOKEN_FILE.read_text(encoding="utf-8").strip()
        request_with_retry(
            self._logger,
            "POST",
            f"{WEB_URL}/results",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "profits": profits,
                "calculated_at": datetime.now(timezone.utc).isoformat(),
                "uptime_seconds": uptime_seconds,
            },
            timeout=10,
        )
