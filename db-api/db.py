import os
import time

import psycopg2

from common.types import ForgeItemInfo


def _get_dsn() -> str:
    host = os.getenv("POSTGRES_HOST", "db")
    dbname = os.getenv("POSTGRES_DB", "skyforge")
    user = os.getenv("POSTGRES_USER", "skyforge")
    password = os.getenv("POSTGRES_PASSWORD", "skyforge")
    connect_timeout = os.getenv("POSTGRES_CONNECT_TIMEOUT", "5")
    return f"host={host} dbname={dbname} user={user} password={password} connect_timeout={connect_timeout}"


def wait_for_db(retries: int = 20, delay: int = 3) -> psycopg2.extensions.connection:
    dsn = _get_dsn()
    for attempt in range(retries):
        try:
            conn: psycopg2.extensions.connection = psycopg2.connect(dsn)
            return conn
        except psycopg2.OperationalError as e:
            if attempt < retries - 1:
                print(f"[db] Not ready yet (attempt {attempt + 1}/{retries}): {e}; retrying in {delay}s...")
                time.sleep(delay)
            else:
                raise RuntimeError(f"Could not connect to database after {retries} attempts") from e
    raise RuntimeError("Unreachable")


def init_schema(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS forge_items (
                name TEXT PRIMARY KEY,
                duration_hours REAL NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS forge_recipes (
                item_name TEXT NOT NULL REFERENCES forge_items(name) ON DELETE CASCADE,
                material  TEXT NOT NULL,
                quantity  INTEGER NOT NULL,
                PRIMARY KEY (item_name, material)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS forge_requirements (
                item_name   TEXT NOT NULL REFERENCES forge_items(name) ON DELETE CASCADE,
                requirement TEXT NOT NULL,
                level       INTEGER NOT NULL,
                PRIMARY KEY (item_name, requirement)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ah_sale_batches (
                id          SERIAL PRIMARY KEY,
                item_name   TEXT NOT NULL,
                quantity    INT  NOT NULL,
                recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_ah_sale_batches_lookup
                ON ah_sale_batches (item_name, recorded_at)
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS market_price_snapshots (
                id          SERIAL PRIMARY KEY,
                item_name   TEXT NOT NULL,
                market      TEXT NOT NULL CHECK (market IN ('Bazaar', 'AH')),
                sell_price  BIGINT NOT NULL,
                sampled_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_market_price_snapshots_lookup
                ON market_price_snapshots (item_name, market, sampled_at)
        """)
    conn.commit()


def upsert_forge_items(conn: psycopg2.extensions.connection, items: dict[str, ForgeItemInfo]) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM forge_items")
        for name, info in items.items():
            cur.execute(
                "INSERT INTO forge_items (name, duration_hours) VALUES (%s, %s)",
                (name, info["Duration"]),
            )
            for material, quantity in info["Recipe"].items():
                cur.execute(
                    "INSERT INTO forge_recipes (item_name, material, quantity) VALUES (%s, %s, %s)",
                    (name, material, quantity),
                )
            for requirement, level in info["Requirements"].items():
                cur.execute(
                    "INSERT INTO forge_requirements (item_name, requirement, level) VALUES (%s, %s, %s)",
                    (name, requirement, level),
                )
    conn.commit()


def read_forge_items(conn: psycopg2.extensions.connection) -> dict[str, ForgeItemInfo]:
    items: dict[str, ForgeItemInfo] = {}

    with conn.cursor() as cur:
        cur.execute("SELECT name, duration_hours FROM forge_items")
        for row in cur.fetchall():
            name: str = row[0]
            duration: float = row[1]
            items[name] = ForgeItemInfo({"Duration": duration, "Recipe": {}, "Requirements": {}})

        cur.execute("SELECT item_name, material, quantity FROM forge_recipes")
        for row in cur.fetchall():
            items[row[0]]["Recipe"][row[1]] = row[2]

        cur.execute("SELECT item_name, requirement, level FROM forge_requirements")
        for row in cur.fetchall():
            items[row[0]]["Requirements"][row[1]] = row[2]

    return items


def insert_ah_sale_batch(conn: psycopg2.extensions.connection, sales: dict[str, int]) -> None:
    with conn.cursor() as cur:
        for item_name, quantity in sales.items():
            cur.execute(
                """
                INSERT INTO ah_sale_batches (item_name, quantity)
                SELECT %s, %s WHERE EXISTS (SELECT 1 FROM forge_items WHERE name = %s)
                """,
                (item_name, quantity, item_name),
            )
        # Prune rows older than 8 days to keep the table lean
        cur.execute("DELETE FROM ah_sale_batches WHERE recorded_at < NOW() - INTERVAL '8 days'")
    conn.commit()


def read_ah_weekly_sales(conn: psycopg2.extensions.connection) -> dict[str, int]:
    """Read 7-day AH sales totals by item.
    Returns {item_name: total_quantity}.
    Estimation logic is handled by the calculator.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                item_name,
                SUM(quantity) as total
            FROM ah_sale_batches
            WHERE recorded_at > NOW() - INTERVAL '7 days'
            GROUP BY item_name
        """)
        result: dict[str, int] = {}
        for row in cur.fetchall():
            item_name, total = row
            result[item_name] = total
        return result


def read_ah_oldest_record_time(conn: psycopg2.extensions.connection) -> str | None:
    """Get the ISO timestamp of the oldest AH sale record in the database.
    Returns None if no records exist.
    Used by calculator to determine actual data collection span for accurate extrapolation.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT MIN(recorded_at) FROM ah_sale_batches")
        result = cur.fetchone()
        if result and result[0]:
            return result[0].isoformat()
        return None


def insert_market_price_snapshots(conn: psycopg2.extensions.connection, snapshots: dict[str, dict[str, int]]) -> None:
    """Insert one sampled sell price per item and market.

    Input format:
    {
        "Item Name": {
            "Bazaar": 12345,
            "AH": 13000,
        }
    }
    """
    with conn.cursor() as cur:
        for item_name, prices_by_market in snapshots.items():
            for market, sell_price in prices_by_market.items():
                if market not in {"Bazaar", "AH"}:
                    continue
                cur.execute(
                    """
                    INSERT INTO market_price_snapshots (item_name, market, sell_price)
                    VALUES (%s, %s, %s)
                    """,
                    (item_name, market, int(sell_price)),
                )
        # Keep eight days of history to support rolling seven-day analytics.
        cur.execute("DELETE FROM market_price_snapshots WHERE sampled_at < NOW() - INTERVAL '8 days'")
    conn.commit()


def read_market_price_stats_7d(conn: psycopg2.extensions.connection) -> dict[str, dict[str, dict[str, int | None]]]:
    """Read seven-day low/high/median sell prices by item and market.

    Returns:
    {
        "Item Name": {
            "Bazaar": {"low": 100, "high": 150, "median": 120, "samples": 42},
            "AH": {"low": 110, "high": 190, "median": 130, "samples": 12},
        }
    }
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH base AS (
                SELECT
                    item_name,
                    market,
                    sell_price
                FROM market_price_snapshots
                WHERE sampled_at > NOW() - INTERVAL '7 days'
            )
            SELECT
                item_name,
                market,
                MIN(sell_price) AS low,
                MAX(sell_price) AS high,
                CAST(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sell_price) AS BIGINT) AS median,
                COUNT(*)::INT AS samples
            FROM base
            GROUP BY item_name, market
            """
        )
        result: dict[str, dict[str, dict[str, int | None]]] = {}
        for row in cur.fetchall():
            item_name, market, low, high, median, samples = row
            item_bucket = result.setdefault(item_name, {})
            item_bucket[market] = {
                "low": low,
                "high": high,
                "median": median,
                "samples": samples,
            }
        return result
