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


def _connect_db() -> psycopg2.extensions.connection:
    logger.info("Waiting for database...")
    connection = db.wait_for_db()
    db.init_schema(connection)
    logger.info("Database ready.")
    return connection


conn: psycopg2.extensions.connection = _connect_db()
last_scraped_at: datetime | None = None
app = flask.Flask(__name__)

T = typing.TypeVar("T")
RouteResponse = flask.Response | tuple[flask.Response, int]


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


@app.put("/forge-items")
def put_forge_items() -> RouteResponse:
    global last_scraped_at
    data = flask.request.get_json(force=True)
    items: dict[str, ForgeItemInfo] = {name: typing.cast(ForgeItemInfo, info) for name, info in data["items"].items()}
    try:
        _run_db_op(lambda connection: db.upsert_forge_items(connection, items), retry_on_disconnect=True)
        last_scraped_at = datetime.now()
        return flask.jsonify({"upserted": len(items)})
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
