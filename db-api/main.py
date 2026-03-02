import logging
import sys
import typing
from datetime import datetime

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
logger.info("Waiting for database...")
conn: psycopg2.extensions.connection = db.wait_for_db()
db.init_schema(conn)
logger.info("Database ready.")
last_scraped_at: datetime | None = None
app = flask.Flask(__name__)


@app.get("/health")
def health() -> flask.Response:
    return flask.jsonify({"status": "ok"})


@app.get("/forge-items")
def get_forge_items() -> flask.Response:
    items = db.read_forge_items(conn)
    return flask.jsonify({"items": items, "last_scraped_at": last_scraped_at.isoformat() if last_scraped_at else None})


@app.put("/forge-items")
def put_forge_items() -> flask.Response:
    global last_scraped_at
    data = flask.request.get_json(force=True)
    items: dict[str, ForgeItemInfo] = {name: typing.cast(ForgeItemInfo, info) for name, info in data["items"].items()}
    db.upsert_forge_items(conn, items)
    last_scraped_at = datetime.now()
    return flask.jsonify({"upserted": len(items)})


@app.post("/ah-sales")
def post_ah_sales() -> flask.Response:
    data = flask.request.get_json(force=True)
    sales: dict[str, int] = {str(k): int(v) for k, v in data["sales"].items()}
    db.insert_ah_sale_batch(conn, sales)
    return flask.jsonify({"recorded": len(sales)})


@app.get("/ah-sales")
def get_ah_sales() -> flask.Response:
    sales = db.read_ah_weekly_sales(conn)
    return flask.jsonify({"sales": sales})


@app.get("/ah-sales/oldest")
def get_ah_sales_oldest() -> flask.Response:
    oldest_at = db.read_ah_oldest_record_time(conn)
    return flask.jsonify({"oldest_recorded_at": oldest_at})
