import logging
import sys
import typing
from pathlib import Path

import db
from db_runtime import DBRuntime, DBUnavailableError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

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
    sales: typing.List[dict[str, int | str | None]]


class BazaarSnapshotsPayload(BaseModel):
    snapshots: dict[str, dict[str, int | None]]


class ErrorResponse(BaseModel):
    error: str


class HealthResponse(BaseModel):
    status: str


class ForgeItemsResponse(BaseModel):
    items: dict[str, ForgeItemInfo]
    last_updated: str | None


class RecordedResponse(BaseModel):
    recorded: int


class MarketSummaryResponse(BaseModel):
    items: dict[str, dict[str, dict[str, int | str | None]]]


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
    last_updated = runtime.last_updated.isoformat() if runtime.last_updated else None
    return ForgeItemsResponse(items=items, last_updated=last_updated)


@app.post("/ah-sales", response_model=RecordedResponse, responses={503: {"model": ErrorResponse}})
def post_ah_sales(payload: AHSalesPayload) -> RecordedResponse:
    sales = payload.sales
    recorded = runtime.run_write(lambda connection: db.insert_ah_sales_with_price(connection, sales))
    return RecordedResponse(recorded=recorded)


@app.post("/bazaar-snapshots", response_model=RecordedResponse, responses={503: {"model": ErrorResponse}})
def post_market_snapshots(payload: BazaarSnapshotsPayload) -> RecordedResponse:
    snapshots = payload.snapshots
    recorded = runtime.run_write(lambda connection: db.insert_bazaar_snapshots(connection, snapshots))
    return RecordedResponse(recorded=recorded)


@app.get("/market-summary", response_model=MarketSummaryResponse, responses={503: {"model": ErrorResponse}})
def get_market_summary() -> MarketSummaryResponse:
    items = runtime.run_read(db.read_market_summary_7d)
    return MarketSummaryResponse(items=items)
