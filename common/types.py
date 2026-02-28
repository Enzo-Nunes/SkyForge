from typing import TypedDict

ForgePageItem = TypedDict(
    "ForgePageItem",
    {
        "Name & Rarity": str,
        "Duration": str,
        "Recipe Tree": list[str],
        "Requirements": str,
    },
)

ForgeItemInfo = TypedDict(
    "ForgeItemInfo",
    {
        "Duration": float,
        "Recipe": dict[str, int],
        "Requirements": dict[str, int],
    },
)

ForgeProfit = TypedDict(
    "ForgeProfit",
    {
        "Rank": int,
        "Name": str,
        "Cost": int,
        "Sell Value": int,
        "Profit": int,
        "Duration": float,
        "Profit per Hour": int,
        "Recipe": dict[str, int],
        "Requirements": dict[str, int],
    },
)
