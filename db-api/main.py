import json
import logging
import sys
import typing
from datetime import datetime
from pathlib import Path

import db
import psycopg2
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

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
PriceStats = dict[str, dict[str, dict[str, int | None]]]


class DBUnavailableError(Exception):
    pass


class AHSalesPayload(BaseModel):
    sales: dict[str, int]


class MarketPricesPayload(BaseModel):
    snapshots: dict[str, dict[str, int]] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: str


class HealthResponse(BaseModel):
    status: str


class ForgeItemsResponse(BaseModel):
    items: dict[str, ForgeItemInfo]
    last_scraped_at: str | None


class RecordedResponse(BaseModel):
    recorded: int


class AHSalesResponse(BaseModel):
    sales: dict[str, int]


class AHSalesOldestResponse(BaseModel):
    oldest_recorded_at: str | None


class MarketPriceStatsResponse(BaseModel):
    stats: PriceStats


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
app = FastAPI()


@app.exception_handler(DBUnavailableError)
async def handle_db_unavailable(_request: Request, _exc: DBUnavailableError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"error": "Database unavailable"})


def _reconnect_db() -> None:
    global conn
    try:
        conn.close()
    except Exception:
        pass
    conn = _connect_db()


def _run_db_op(operation: typing.Callable[[psycopg2.extensions.connection], T], *, retry_on_disconnect: bool) -> T:
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


def _run_db_read(operation: typing.Callable[[psycopg2.extensions.connection], T]) -> T:
    try:
        return _run_db_op(operation, retry_on_disconnect=True)
    except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
        logger.warning(f"DB read failed: {e}")
        raise DBUnavailableError from e


def _run_db_write(operation: typing.Callable[[psycopg2.extensions.connection], T]) -> T:
    try:
        return _run_db_op(operation, retry_on_disconnect=False)
    except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
        _reconnect_db()
        logger.warning(f"DB write failed: {e}")
        raise DBUnavailableError from e


@app.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/forge-items", response_model=ForgeItemsResponse, responses={503: {"model": ErrorResponse}})
def get_forge_items() -> ForgeItemsResponse:
    items: dict[str, ForgeItemInfo] = _run_db_read(db.read_forge_items)
    return ForgeItemsResponse(items=items, last_scraped_at=last_scraped_at.isoformat() if last_scraped_at else None)


@app.post("/ah-sales", response_model=RecordedResponse, responses={503: {"model": ErrorResponse}})
def post_ah_sales(payload: AHSalesPayload) -> RecordedResponse:
    sales = payload.sales
    _run_db_write(lambda connection: db.insert_ah_sale_batch(connection, sales))
    return RecordedResponse(recorded=len(sales))


@app.post("/market-prices", response_model=RecordedResponse, responses={503: {"model": ErrorResponse}})
def post_market_prices(payload: MarketPricesPayload) -> RecordedResponse:
    snapshots = payload.snapshots

    _run_db_write(lambda connection: db.insert_market_price_snapshots(connection, snapshots))
    return RecordedResponse(recorded=len(snapshots))


@app.get("/ah-sales", response_model=AHSalesResponse, responses={503: {"model": ErrorResponse}})
def get_ah_sales() -> AHSalesResponse:
    sales = _run_db_read(db.read_ah_weekly_sales)
    return AHSalesResponse(sales=sales)


@app.get("/ah-sales/oldest", response_model=AHSalesOldestResponse, responses={503: {"model": ErrorResponse}})
def get_ah_sales_oldest() -> AHSalesOldestResponse:
    oldest_at = _run_db_read(db.read_ah_oldest_record_time)
    return AHSalesOldestResponse(oldest_recorded_at=oldest_at)


@app.get("/market-prices/stats", response_model=MarketPriceStatsResponse, responses={503: {"model": ErrorResponse}})
def get_market_price_stats() -> MarketPriceStatsResponse:
    stats = _run_db_read(db.read_market_price_stats_7d)
    return MarketPriceStatsResponse(stats=stats)
