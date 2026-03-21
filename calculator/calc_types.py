import typing

DB_API_URL = "http://db-api:5000"

PriceStats: typing.TypeAlias = dict[str, dict[str, dict[str, int | None]]]

ForgeProfit = typing.TypedDict(
    "ForgeProfit",
    {
        "Rank": int,
        "Name": str,
        "Cost": int,
        "Sell Value": int,
        "Profit": int,
        "Duration": float,
        "Profit per Hour": int,
        "Weekly Volume": int,
        "Volume Estimated": bool,
        "AH Raw Volume Window": int | None,
        "Data Span Seconds": int | None,
        "Selling Market": str,
        "Price Samples 7d": int,
        "Sell Price Low 7d": int | None,
        "Sell Price High 7d": int | None,
        "Sell Price Median 7d": int | None,
        "Sell Price Range % 7d": int | None,
        "Recipe Markets": dict[str, str],
        "Recipe": dict[str, int],
        "Requirements": dict[str, int],
    },
)
