import json
import logging
import sys
import typing
from datetime import datetime
from pathlib import Path

import db
import flask
import psycopg2

from common.types import ForgeItemInfo

_formatter = logging.Formatter("%(asctime)s - db-api - %(levelname)s - %(message)s")
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(_formatter)
logger = logging.getLogger("db-api")
logger.handlers.clear()
logger.addHandler(_handler)
logger.setLevel(logging.INFO)
logger.propagate = False

FORGE_DATA_PATH = Path(__file__).with_name("forge_data.json")

T = typing.TypeVar("T")
RouteResponse = flask.Response | tuple[flask.Response, int]


def _coerce_int(value: object, *, context: str) -> int:
    if not isinstance(value, int | float | str):
        raise RuntimeError(f"forge_data.json {context} must be numeric")

    try:
        return int(value)
    except (TypeError, ValueError) as e:
        raise RuntimeError(f"forge_data.json {context} must be numeric") from e


def _load_forge_items() -> tuple[dict[str, ForgeItemInfo], datetime | None]:
    if not FORGE_DATA_PATH.exists():
        raise RuntimeError(f"Missing forge file at {FORGE_DATA_PATH}")

    with FORGE_DATA_PATH.open("r", encoding="utf-8") as file:
        raw_obj: object = json.load(file)

    if not isinstance(raw_obj, dict):
        raise RuntimeError("forge_data.json root must be an object")

    raw = typing.cast(dict[object, object], raw_obj)

    raw_items_obj = raw.get("items")
    if not isinstance(raw_items_obj, dict) or not raw_items_obj:
        raise RuntimeError("forge_data.json must contain a non-empty 'items' object")

    raw_items = typing.cast(dict[object, object], raw_items_obj)

    items: dict[str, ForgeItemInfo] = {}
    for name_obj, info_obj in raw_items.items():
        if not isinstance(name_obj, str) or not isinstance(info_obj, dict):
            raise RuntimeError("forge_data.json contains invalid item entries")

        name = name_obj
        info = typing.cast(dict[object, object], info_obj)
        duration_obj = info.get("Duration")
        recipe_obj = info.get("Recipe")
        requirements_obj = info.get("Requirements")

        if not isinstance(duration_obj, int | float | str):
            raise RuntimeError(f"forge_data.json item '{name}' has invalid Duration")
        if not isinstance(recipe_obj, dict):
            raise RuntimeError(f"forge_data.json item '{name}' has invalid Recipe")
        if not isinstance(requirements_obj, dict):
            raise RuntimeError(f"forge_data.json item '{name}' has invalid Requirements")

        recipe: dict[str, int] = {}
        for material_obj, quantity_obj in typing.cast(dict[object, object], recipe_obj).items():
            recipe[str(material_obj)] = _coerce_int(quantity_obj, context=f"item '{name}' recipe quantity")

        requirements: dict[str, int] = {}
        for requirement_obj, level_obj in typing.cast(dict[object, object], requirements_obj).items():
            requirements[str(requirement_obj)] = _coerce_int(level_obj, context=f"item '{name}' requirement level")

        duration = float(duration_obj)
        items[name] = ForgeItemInfo({"Duration": duration, "Recipe": recipe, "Requirements": requirements})

    last_updated: datetime | None = None
    raw_meta_obj = raw.get("meta")
    if isinstance(raw_meta_obj, dict):
        raw_meta = typing.cast(dict[object, object], raw_meta_obj)
        raw_date_updated = raw_meta.get("date_updated")
        if isinstance(raw_date_updated, str):
            try:
                last_updated = datetime.fromisoformat(raw_date_updated)
            except ValueError:
                logger.warning("Invalid meta.date_updated in forge_data.json; using startup time")

    return items, last_updated


def _connect_db() -> psycopg2.extensions.connection:
    global last_scraped_at
    logger.info("Waiting for database...")
    connection = db.wait_for_db()
    db.init_schema(connection)
    items, last_updated = _load_forge_items()
    db.upsert_forge_items(connection, items)
    last_scraped_at = last_updated or datetime.now()
    logger.info(f"Loaded {len(items)} forge items from {FORGE_DATA_PATH.name}")
    logger.info("Database ready.")
    return connection


last_scraped_at: datetime | None = None
conn: psycopg2.extensions.connection = _connect_db()
app = flask.Flask(__name__)


def _reconnect_db() -> None:
    global conn
    try:
        conn.close()
    except Exception:
        pass
    conn = _connect_db()


def _run_db_op(
    operation: typing.Callable[[psycopg2.extensions.connection], T],
    *,
    retry_on_disconnect: bool,
) -> T:
    global conn
    for attempt in range(2):
        try:
            if conn.closed:
                raise psycopg2.InterfaceError("Database connection is closed")
            return operation(conn)
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            if attempt == 1 or not retry_on_disconnect:
                raise
            logger.warning(f"Database connection lost ({e}). Reconnecting and retrying request...")
            _reconnect_db()

    raise RuntimeError("Unreachable")


@app.get("/health")
def health() -> RouteResponse:
    return flask.jsonify({"status": "ok"})


@app.get("/forge-items")
def get_forge_items() -> RouteResponse:
    try:
        items = _run_db_op(db.read_forge_items, retry_on_disconnect=True)
        return flask.jsonify(
            {"items": items, "last_scraped_at": last_scraped_at.isoformat() if last_scraped_at else None}
        )
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        return flask.jsonify({"error": "Database unavailable"}), 503


@app.post("/ah-sales")
def post_ah_sales() -> RouteResponse:
    data = flask.request.get_json(force=True)
    sales: dict[str, int] = {str(k): int(v) for k, v in data["sales"].items()}
    try:
        _run_db_op(lambda connection: db.insert_ah_sale_batch(connection, sales), retry_on_disconnect=False)
        return flask.jsonify({"recorded": len(sales)})
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        _reconnect_db()
        return flask.jsonify({"error": "Database unavailable"}), 503


@app.post("/market-prices")
def post_market_prices() -> RouteResponse:
    data = flask.request.get_json(force=True)
    raw_snapshots = typing.cast(dict[str, dict[str, typing.Any]], data.get("snapshots", {}))
    snapshots: dict[str, dict[str, int]] = {}
    for item_name, markets in raw_snapshots.items():
        snapshots[item_name] = {}
        for market, price in markets.items():
            snapshots[item_name][market] = int(price)

    try:
        _run_db_op(
            lambda connection: db.insert_market_price_snapshots(connection, snapshots), retry_on_disconnect=False
        )
        return flask.jsonify({"recorded": len(snapshots)})
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        _reconnect_db()
        return flask.jsonify({"error": "Database unavailable"}), 503


@app.get("/ah-sales")
def get_ah_sales() -> RouteResponse:
    try:
        sales = _run_db_op(db.read_ah_weekly_sales, retry_on_disconnect=True)
        return flask.jsonify({"sales": sales})
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        return flask.jsonify({"error": "Database unavailable"}), 503


@app.get("/ah-sales/oldest")
def get_ah_sales_oldest() -> RouteResponse:
    try:
        oldest_at = _run_db_op(db.read_ah_oldest_record_time, retry_on_disconnect=True)
        return flask.jsonify({"oldest_recorded_at": oldest_at})
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        return flask.jsonify({"error": "Database unavailable"}), 503


@app.get("/market-prices/stats")
def get_market_price_stats() -> RouteResponse:
    try:
        stats = _run_db_op(db.read_market_price_stats_7d, retry_on_disconnect=True)
        return flask.jsonify({"stats": stats})
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        return flask.jsonify({"error": "Database unavailable"}), 503
