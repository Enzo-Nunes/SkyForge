import typing

ForgePageItem = typing.TypedDict(
    "ForgePageItem",
    {
        "Name & Rarity": str,
        "Duration": str,
        "Recipe Tree": list[str],
        "Requirements": str,
    },
)

ForgeItemInfo = typing.TypedDict(
    "ForgeItemInfo",
    {
        "Duration": float,
        "Recipe": dict[str, int],
        "Requirements": dict[str, int],
    },
)

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
