import typing

ForgeItemInfo = typing.TypedDict(
    "ForgeItemInfo",
    {
        "Duration": float,
        "Recipe": dict[str, int],
        "Requirements": dict[str, int],
    },
)
