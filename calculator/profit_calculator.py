import logging
import math
import time
import typing
from datetime import datetime, timezone

from calc_http import request_with_retry
from calc_types import DB_API_URL, ForgeProfit, PriceStats
from market_tracker import ForgeItemState, MarketPriceTracker

from common.types import ForgeItemInfo


class ProfitCalculator:
    MIN_AH_SALES_FOR_EXTRAPOLATION = 3

    def __init__(self, logger: logging.Logger, market: MarketPriceTracker, item_state: ForgeItemState) -> None:
        self._logger = logger
        self._market = market
        self._item_state = item_state
        self._start_time = time.time()

    def calculate_profits(self, forge_info: dict[str, ForgeItemInfo]) -> tuple[list[ForgeProfit], int | None]:
        auction_house_prices = self._market.get_auction_house_prices_snapshot()
        bazaar_prices = self._market.fetch_bazaar_prices(self._item_state.get_tracked_items())
        price_stats_7d: PriceStats = {}
        uptime_seconds = int(time.time() - self._start_time)
        ah_weekly_sales: dict[str, int] = {}
        ah_raw_sales_window: dict[str, int] = {}
        ah_volume_estimated: dict[str, bool] = {}
        ah_data_span_seconds_by_item: dict[str, int] = {}
        bazaar_data_span_seconds_by_item: dict[str, int] = {}

        try:
            response = request_with_retry(self._logger, "GET", f"{DB_API_URL}/market-summary", timeout=10)
            market_summary = response.json().get("items", {})
            self._logger.info(f"Fetched {len(market_summary)} items from market summary data")

            now_dt = datetime.now(timezone.utc)
            for item_name, market_stats_obj in market_summary.items():
                market_stats = typing.cast(dict[str, dict[str, int | str | None]], market_stats_obj)

                ah_stats = market_stats.get("AH", {})
                quantity_raw = ah_stats.get("quantity")
                quantity = int(quantity_raw) if isinstance(quantity_raw, int) else 0
                ah_raw_sales_window[item_name] = quantity

                low = ah_stats.get("low")
                high = ah_stats.get("high")
                median = ah_stats.get("median")
                price_stats_7d[item_name] = {
                    "AH": {
                        "low": int(low) if isinstance(low, int) else None,
                        "high": int(high) if isinstance(high, int) else None,
                        "median": int(median) if isinstance(median, int) else None,
                        "samples": quantity,
                    }
                }

                bazaar_stats = market_stats.get("Bazaar", {})
                bazaar_quantity_raw = bazaar_stats.get("quantity")
                bazaar_quantity = int(bazaar_quantity_raw) if isinstance(bazaar_quantity_raw, int) else 0
                bazaar_low = bazaar_stats.get("low")
                bazaar_high = bazaar_stats.get("high")
                bazaar_median = bazaar_stats.get("median")
                price_stats_7d[item_name]["Bazaar"] = {
                    "low": int(bazaar_low) if isinstance(bazaar_low, int) else None,
                    "high": int(bazaar_high) if isinstance(bazaar_high, int) else None,
                    "median": int(bazaar_median) if isinstance(bazaar_median, int) else None,
                    "samples": bazaar_quantity,
                }

                bazaar_oldest_recorded_at_raw = bazaar_stats.get("oldest_recorded_at")
                if isinstance(bazaar_oldest_recorded_at_raw, str):
                    bazaar_oldest_dt = datetime.fromisoformat(bazaar_oldest_recorded_at_raw)
                    if bazaar_oldest_dt.tzinfo is None:
                        bazaar_oldest_dt = bazaar_oldest_dt.replace(tzinfo=timezone.utc)
                    bazaar_data_span_seconds_by_item[item_name] = max(
                        1, int((now_dt - bazaar_oldest_dt).total_seconds())
                    )

                oldest_recorded_at_raw = ah_stats.get("oldest_recorded_at")
                if isinstance(oldest_recorded_at_raw, str):
                    oldest_dt = datetime.fromisoformat(oldest_recorded_at_raw)
                    if oldest_dt.tzinfo is None:
                        oldest_dt = oldest_dt.replace(tzinfo=timezone.utc)
                    span_seconds = max(1, int((now_dt - oldest_dt).total_seconds()))
                    ah_data_span_seconds_by_item[item_name] = span_seconds
                    if span_seconds < 604800 and quantity >= self.MIN_AH_SALES_FOR_EXTRAPOLATION:
                        ah_weekly_sales[item_name] = int(quantity * 604800 / span_seconds)
                        ah_volume_estimated[item_name] = True
                    else:
                        ah_weekly_sales[item_name] = quantity
                        ah_volume_estimated[item_name] = False
                else:
                    ah_weekly_sales[item_name] = quantity
                    ah_volume_estimated[item_name] = False
        except Exception as e:
            self._logger.warning(f"Could not fetch AH weekly sales: {e}")
            ah_weekly_sales = {}
            ah_raw_sales_window = {}
            ah_volume_estimated = {}
            ah_data_span_seconds_by_item = {}
            bazaar_data_span_seconds_by_item = {}

        self._logger.info("Starting final profit calculations...")
        items_profit: list[ForgeProfit] = []

        for item_name in forge_info.keys():
            item_info = forge_info[item_name]
            duration = item_info["Duration"]
            item_cost = 0
            is_craftable = True
            is_sellable = True
            recipe_markets: dict[str, str] = {}

            for material in item_info["Recipe"].keys():
                material_bazaar_info = bazaar_prices.get(material)
                if material_bazaar_info:
                    material_price = material_bazaar_info.get("Buy Price", -1)
                    recipe_markets[material] = "Bazaar"
                else:
                    material_price = auction_house_prices.get(material, -1)
                    recipe_markets[material] = "AH"
                if material_price < 0:
                    is_craftable = False
                item_cost += item_info["Recipe"][material] * material_price

            ah_raw_volume_window: int | None = None
            item_bazaar_info = bazaar_prices.get(item_name)
            if item_bazaar_info:
                item_sell_price = item_bazaar_info.get("Sell Price", -1)
                weekly_volume = int(item_bazaar_info.get("Weekly Volume", 0) or 0)
                volume_source = "Bazaar"
                volume_estimated = False
            else:
                item_sell_price = auction_house_prices.get(item_name, -1)
                weekly_volume = ah_weekly_sales.get(item_name, 0)
                volume_source = "AH"
                volume_estimated = ah_volume_estimated.get(item_name, False)
                ah_raw_volume_window = ah_raw_sales_window.get(item_name)

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

            data_span_seconds: int | None = None
            if volume_source == "AH":
                data_span_seconds = ah_data_span_seconds_by_item.get(item_name)
            elif volume_source == "Bazaar":
                data_span_seconds = bazaar_data_span_seconds_by_item.get(item_name)

            if is_craftable and is_sellable and item_sell_price > item_cost:
                items_profit.append(
                    {
                        "Rank": 0,
                        "Name": item_name,
                        "Cost": math.ceil(item_cost),
                        "Sell Value": math.ceil(item_sell_price),
                        "Profit": math.ceil(item_sell_price - item_cost),
                        "Duration": duration,
                        "Profit per Hour": math.ceil((item_sell_price - item_cost) / duration),
                        "Weekly Volume": weekly_volume,
                        "Volume Estimated": volume_estimated,
                        "AH Raw Volume Window": ah_raw_volume_window,
                        "Data Span Seconds": data_span_seconds,
                        "Selling Market": volume_source,
                        "Price Samples 7d": samples_7d,
                        "Sell Price Low 7d": low_7d,
                        "Sell Price High 7d": high_7d,
                        "Sell Price Median 7d": median_7d,
                        "Sell Price Range % 7d": range_pct_7d,
                        "Recipe Markets": recipe_markets,
                        "Recipe": item_info["Recipe"],
                        "Requirements": item_info["Requirements"],
                    }
                )

        return (
            [
                typing.cast(ForgeProfit, {**item, "Rank": i + 1})
                for i, item in enumerate(sorted(items_profit, key=lambda x: x["Profit per Hour"], reverse=True))
            ],
            uptime_seconds,
        )
