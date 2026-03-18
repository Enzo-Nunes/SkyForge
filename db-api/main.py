import logging
import sys
from pathlib import Path

import db
from db_runtime import DBRuntime, DBUnavailableError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from common.types import ForgeItemInfo

FORGE_DATA_PATH = Path(__file__).with_name("forge_data.json")

_formatter = logging.Formatter("%(asctime)s - db-api - %(levelname)s - %(message)s")
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(_formatter)
logger = logging.getLogger("db-api")
logger.handlers.clear()
logger.addHandler(_handler)
logger.setLevel(logging.INFO)
logger.propagate = False


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
    stats: dict[str, dict[str, dict[str, int | None]]]


runtime = DBRuntime(logger, FORGE_DATA_PATH)
app = FastAPI()


@app.exception_handler(DBUnavailableError)
async def handle_db_unavailable(_request: Request, _exc: DBUnavailableError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"error": "Database unavailable"})


@app.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/forge-items", response_model=ForgeItemsResponse, responses={503: {"model": ErrorResponse}})
def get_forge_items() -> ForgeItemsResponse:
    items: dict[str, ForgeItemInfo] = runtime.run_read(db.read_forge_items)
    last_scraped_at = runtime.last_scraped_at.isoformat() if runtime.last_scraped_at else None
    return ForgeItemsResponse(items=items, last_scraped_at=last_scraped_at)


@app.post("/ah-sales", response_model=RecordedResponse, responses={503: {"model": ErrorResponse}})
def post_ah_sales(payload: AHSalesPayload) -> RecordedResponse:
    sales = payload.sales
    runtime.run_write(lambda connection: db.insert_ah_sale_batch(connection, sales))
    return RecordedResponse(recorded=len(sales))


@app.post("/market-prices", response_model=RecordedResponse, responses={503: {"model": ErrorResponse}})
def post_market_prices(payload: MarketPricesPayload) -> RecordedResponse:
    snapshots = payload.snapshots

    runtime.run_write(lambda connection: db.insert_market_price_snapshots(connection, snapshots))
    return RecordedResponse(recorded=len(snapshots))


@app.get("/ah-sales", response_model=AHSalesResponse, responses={503: {"model": ErrorResponse}})
def get_ah_sales() -> AHSalesResponse:
    sales = runtime.run_read(db.read_ah_weekly_sales)
    return AHSalesResponse(sales=sales)


@app.get("/ah-sales/oldest", response_model=AHSalesOldestResponse, responses={503: {"model": ErrorResponse}})
def get_ah_sales_oldest() -> AHSalesOldestResponse:
    oldest_at = runtime.run_read(db.read_ah_oldest_record_time)
    return AHSalesOldestResponse(oldest_recorded_at=oldest_at)


@app.get("/market-prices/stats", response_model=MarketPriceStatsResponse, responses={503: {"model": ErrorResponse}})
def get_market_price_stats() -> MarketPriceStatsResponse:
    stats = runtime.run_read(db.read_market_price_stats_7d)
    return MarketPriceStatsResponse(stats=stats)
