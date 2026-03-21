import json
import logging
import typing
from datetime import datetime
from pathlib import Path

from common.types import ForgeItemInfo


class ForgeSeedItem(typing.TypedDict):
    Duration: int | float | str
    Recipe: dict[str, int | float | str]
    Requirements: dict[str, int | float | str]


class ForgeSeedMeta(typing.TypedDict, total=False):
    date_updated: str


class ForgeSeedPayload(typing.TypedDict):
    items: dict[str, ForgeSeedItem]
    meta: ForgeSeedMeta


def _coerce_int(value: object, *, context: str) -> int:
    if not isinstance(value, int | float | str):
        raise RuntimeError(f"forge_data.json {context} must be numeric")

    try:
        return int(value)
    except (TypeError, ValueError) as e:
        raise RuntimeError(f"forge_data.json {context} must be numeric") from e


def _coerce_item(raw_item: object, *, name: str) -> ForgeSeedItem:
    if not isinstance(raw_item, dict):
        raise RuntimeError("forge_data.json contains invalid item entries")

    raw_item_map = typing.cast(dict[object, object], raw_item)

    duration_obj = raw_item_map.get("Duration")
    recipe_obj = raw_item_map.get("Recipe")
    requirements_obj = raw_item_map.get("Requirements")

    if not isinstance(duration_obj, int | float | str):
        raise RuntimeError(f"forge_data.json item '{name}' has invalid Duration")
    if not isinstance(recipe_obj, dict):
        raise RuntimeError(f"forge_data.json item '{name}' has invalid Recipe")
    if not isinstance(requirements_obj, dict):
        raise RuntimeError(f"forge_data.json item '{name}' has invalid Requirements")

    recipe_map = typing.cast(dict[object, object], recipe_obj)
    requirements_map = typing.cast(dict[object, object], requirements_obj)

    recipe: dict[str, int | float | str] = {}
    for material_obj, quantity_obj in recipe_map.items():
        recipe[str(material_obj)] = typing.cast(int | float | str, quantity_obj)

    requirements: dict[str, int | float | str] = {}
    for requirement_obj, level_obj in requirements_map.items():
        requirements[str(requirement_obj)] = typing.cast(int | float | str, level_obj)

    return ForgeSeedItem(
        {
            "Duration": duration_obj,
            "Recipe": recipe,
            "Requirements": requirements,
        }
    )


def _coerce_seed_payload(raw_obj: object) -> ForgeSeedPayload:
    if not isinstance(raw_obj, dict):
        raise RuntimeError("forge_data.json root must be an object")

    raw_root = typing.cast(dict[object, object], raw_obj)

    raw_items_obj = raw_root.get("items")
    if not isinstance(raw_items_obj, dict) or not raw_items_obj:
        raise RuntimeError("forge_data.json must contain a non-empty 'items' object")

    raw_items_map = typing.cast(dict[object, object], raw_items_obj)

    items: dict[str, ForgeSeedItem] = {}
    for name_obj, info_obj in raw_items_map.items():
        if not isinstance(name_obj, str):
            raise RuntimeError("forge_data.json contains invalid item entries")
        items[name_obj] = _coerce_item(info_obj, name=name_obj)

    meta: ForgeSeedMeta = {}
    raw_meta_obj = raw_root.get("meta")
    if isinstance(raw_meta_obj, dict):
        raw_meta_map = typing.cast(dict[object, object], raw_meta_obj)
        raw_date_updated = raw_meta_map.get("date_updated")
        if isinstance(raw_date_updated, str):
            meta["date_updated"] = raw_date_updated

    return ForgeSeedPayload({"items": items, "meta": meta})


def load_forge_items(path: Path, logger: logging.Logger) -> tuple[dict[str, ForgeItemInfo], datetime | None]:
    if not path.exists():
        raise RuntimeError(f"Missing forge file at {path}")

    with path.open("r", encoding="utf-8") as file:
        raw_obj: object = json.load(file)

    seed_payload = _coerce_seed_payload(raw_obj)

    items: dict[str, ForgeItemInfo] = {}
    for name, info in seed_payload["items"].items():
        recipe: dict[str, int] = {}
        for material, quantity in info["Recipe"].items():
            recipe[material] = _coerce_int(quantity, context=f"item '{name}' recipe quantity")

        requirements: dict[str, int] = {}
        for requirement, level in info["Requirements"].items():
            requirements[requirement] = _coerce_int(level, context=f"item '{name}' requirement level")

        duration = float(info["Duration"])
        items[name] = ForgeItemInfo({"Duration": duration, "Recipe": recipe, "Requirements": requirements})

    last_updated: datetime | None = None
    raw_date_updated = seed_payload["meta"].get("date_updated")
    if isinstance(raw_date_updated, str):
        try:
            last_updated = datetime.fromisoformat(raw_date_updated)
        except ValueError:
            logger.warning("Invalid meta.date_updated in forge_data.json; using startup time")

    return items, last_updated
