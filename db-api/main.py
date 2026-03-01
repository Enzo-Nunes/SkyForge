import logging
import sys
from datetime import datetime
from typing import cast

import psycopg2.extensions
from db import (
    init_schema,
    insert_ah_sale_batch,
    read_ah_weekly_sales,
    read_forge_items,
    upsert_forge_items,
    wait_for_db,
)
from flask import Flask, Response, jsonify, request

from common.types import ForgeItemInfo

_formatter = logging.Formatter("%(asctime)s - db-api - %(levelname)s - %(message)s")
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(_formatter)
logger = logging.getLogger("db-api")
logger.handlers.clear()
logger.addHandler(_handler)
logger.setLevel(logging.INFO)
logger.propagate = False
logger.info("Waiting for database...")
conn: psycopg2.extensions.connection = wait_for_db()
init_schema(conn)
logger.info("Database ready.")
last_scraped_at: datetime | None = None
app = Flask(__name__)


@app.get("/health")
def health() -> Response:
    return jsonify({"status": "ok"})


@app.get("/forge-items")
def get_forge_items() -> Response:
    items = read_forge_items(conn)
    return jsonify({"items": items, "last_scraped_at": last_scraped_at.isoformat() if last_scraped_at else None})


@app.put("/forge-items")
def put_forge_items() -> Response:
    global last_scraped_at
    data = request.get_json(force=True)
    items: dict[str, ForgeItemInfo] = {name: cast(ForgeItemInfo, info) for name, info in data["items"].items()}
    upsert_forge_items(conn, items)
    last_scraped_at = datetime.now()
    return jsonify({"upserted": len(items)})


@app.post("/ah-sales")
def post_ah_sales() -> Response:
    data = request.get_json(force=True)
    sales: dict[str, int] = {str(k): int(v) for k, v in data["sales"].items()}
    insert_ah_sale_batch(conn, sales)
    return jsonify({"recorded": len(sales)})


@app.get("/ah-sales")
def get_ah_sales() -> Response:
    sales = read_ah_weekly_sales(conn)
    return jsonify({"sales": sales})
