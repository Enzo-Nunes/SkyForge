import logging
import math
import time
import typing
from datetime import datetime, timezone

from calc_http import request_with_retry
from calc_types import ForgeProfit, PriceStats
from constants import DB_API_URL
from hypixel_client import MarketPriceTracker

from common.types import ForgeItemInfo


class ProfitCalculator:
    def __init__(self, logger: logging.Logger, market: MarketPriceTracker) -> None:
        self._logger = logger
        self._market = market
        self._start_time = time.time()

    @property
    def market(self) -> MarketPriceTracker:
        return self._market

    def _store_price_snapshots(
        self,
        forge_info: dict[str, ForgeItemInfo],
        auction_house_prices: dict[str, int],
        bazaar_prices: dict[str, dict[str, int]],
    ) -> None:
        snapshots: dict[str, dict[str, int]] = {}
        for item_name in forge_info.keys():
            item_snapshots: dict[str, int] = {}

            bazaar_sell = bazaar_prices.get(item_name, {}).get("Sell Price", -1)
            if bazaar_sell and bazaar_sell > 0:
                item_snapshots["Bazaar"] = int(bazaar_sell)

            ah_sell = auction_house_prices.get(item_name, -1)
            if ah_sell and ah_sell > 0:
                item_snapshots["AH"] = int(ah_sell)

            if item_snapshots:
                snapshots[item_name] = item_snapshots

        if not snapshots:
            return

        request_with_retry(
            self._logger, "POST", f"{DB_API_URL}/market-prices", json={"snapshots": snapshots}, timeout=15
        )

    def _read_price_stats(self) -> PriceStats:
        response = request_with_retry(self._logger, "GET", f"{DB_API_URL}/market-prices/stats", timeout=15)
        return typing.cast(PriceStats, response.json().get("stats", {}))

    def calculate_profits(self, forge_info: dict[str, ForgeItemInfo]) -> tuple[list[ForgeProfit], int | None]:
        auction_house_prices = self._market.fetch_auction_house_prices()
        bazaar_prices = self._market.fetch_bazaar_prices()

        price_stats_7d: PriceStats = {}
        try:
            self._store_price_snapshots(forge_info, auction_house_prices, bazaar_prices)
            price_stats_7d = self._read_price_stats()
        except Exception as e:
            self._logger.warning(f"Could not store/read market price history: {e}")

        uptime_seconds = int(time.time() - self._start_time)

        ah_weekly_sales: dict[str, int] = {}
        ah_volume_estimated: dict[str, bool] = {}

        try:
            oldest_response = request_with_retry(self._logger, "GET", f"{DB_API_URL}/ah-sales/oldest", timeout=10)
            oldest_recorded_at_str = oldest_response.json().get("oldest_recorded_at")

            data_span_seconds = 604800
            is_estimated = uptime_seconds < 604800

            if oldest_recorded_at_str:
                oldest_dt = datetime.fromisoformat(oldest_recorded_at_str)
                now_dt = datetime.now(timezone.utc)
                data_span_seconds = max(1, int((now_dt - oldest_dt).total_seconds()))
                self._logger.info(
                    f"AH data collection: oldest record at {oldest_recorded_at_str}, "
                    f"span = {data_span_seconds}s ({data_span_seconds / 86400:.2f} days)"
                )
            else:
                self._logger.info("No AH records in database yet, will not extrapolate")

            self._logger.info(
                f"Tool uptime: {uptime_seconds}s ({uptime_seconds / 86400:.2f} days), "
                f"is_estimated flag = {is_estimated}"
            )

            response = request_with_retry(self._logger, "GET", f"{DB_API_URL}/ah-sales", timeout=10)
            ah_sales_data = response.json().get("sales", {})
            self._logger.info(f"Fetched {len(ah_sales_data)} items from AH sales data")

            for item_name, total_quantity in ah_sales_data.items():
                if is_estimated:
                    volume = int(total_quantity * 604800 / data_span_seconds)
                    self._logger.debug(
                        f"  {item_name}: raw_qty={total_quantity}, "
                        f"extrapolated={volume} (qty × 604800 / {data_span_seconds})"
                    )
                else:
                    volume = total_quantity
                ah_weekly_sales[item_name] = volume
                ah_volume_estimated[item_name] = is_estimated
        except Exception as e:
            self._logger.warning(f"Could not fetch AH weekly sales: {e}")
            ah_weekly_sales = {}
            ah_volume_estimated = {}

        self._logger.info("Starting final profit calculations...")
        items_profit: list[ForgeProfit] = []

        for item_name in forge_info.keys():
            item_cost = 0
            is_craftable = True
            is_sellable = True
            recipe_markets: dict[str, str] = {}

            for material in forge_info[item_name]["Recipe"].keys():
                material_bazaar_info = bazaar_prices.get(material)
                if material_bazaar_info:
                    material_price = material_bazaar_info.get("Buy Price", -1)
                    recipe_markets[material] = "Bazaar"
                else:
                    material_price = auction_house_prices.get(material, -1)
                    recipe_markets[material] = "AH"
                if material_price < 0:
                    is_craftable = False
                item_cost += forge_info[item_name]["Recipe"][material] * material_price

            item_bazaar_info = bazaar_prices.get(item_name)
            if item_bazaar_info:
                item_sell_price = item_bazaar_info.get("Sell Price", -1)
                weekly_volume = item_bazaar_info.get("Weekly Volume", 0)
                volume_source = "Bazaar"
                volume_estimated = False
            else:
                item_sell_price = auction_house_prices.get(item_name, -1)
                weekly_volume = ah_weekly_sales.get(item_name, 0)
                volume_source = "AH"
                volume_estimated = ah_volume_estimated.get(item_name, False)

            item_price_stats = price_stats_7d.get(item_name, {}).get(volume_source, {})
            low_7d = item_price_stats.get("low")
            high_7d = item_price_stats.get("high")
            median_7d = item_price_stats.get("median")
            samples_7d = int(item_price_stats.get("samples", 0) or 0)
            range_pct_7d: int | None = None
            if median_7d and median_7d > 0 and low_7d is not None and high_7d is not None:
                range_pct_7d = int(round(((high_7d - low_7d) / median_7d) * 100))

            if item_sell_price < 0:
                is_sellable = False

            if is_craftable and is_sellable and item_sell_price > item_cost:
                items_profit.append(
                    {
                        "Rank": 0,
                        "Name": item_name,
                        "Cost": math.ceil(item_cost),
                        "Sell Value": math.ceil(item_sell_price),
                        "Profit": math.ceil(item_sell_price - item_cost),
                        "Duration": forge_info[item_name]["Duration"],
                        "Profit per Hour": math.ceil((item_sell_price - item_cost) / forge_info[item_name]["Duration"]),
                        "Weekly Volume": weekly_volume,
                        "Volume Estimated": volume_estimated,
                        "Selling Market": volume_source,
                        "Price Samples 7d": samples_7d,
                        "Sell Price Low 7d": low_7d,
                        "Sell Price High 7d": high_7d,
                        "Sell Price Median 7d": median_7d,
                        "Sell Price Range % 7d": range_pct_7d,
                        "Recipe Markets": recipe_markets,
                        "Recipe": forge_info[item_name]["Recipe"],
                        "Requirements": forge_info[item_name]["Requirements"],
                    }
                )

        return (
            [
                typing.cast(ForgeProfit, {**item, "Rank": i + 1})
                for i, item in enumerate(sorted(items_profit, key=lambda x: x["Profit per Hour"], reverse=True))
            ],
            uptime_seconds,
        )
