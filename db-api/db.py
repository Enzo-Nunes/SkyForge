import os
import time
import typing

import psycopg2

from common.types import ForgeItemInfo

ForgeItemRow: typing.TypeAlias = tuple[str, float]
ForgeRecipeRow: typing.TypeAlias = tuple[str, str, int]
ForgeRequirementRow: typing.TypeAlias = tuple[str, str, int]
AHSalesSummaryRow: typing.TypeAlias = tuple[str, int | None, int | None, int | None, int, str | None]
BazaarSummaryRow: typing.TypeAlias = tuple[str, int | None, int | None, int | None, int, str | None]


def _get_dsn() -> str:
    host = os.getenv("POSTGRES_HOST", "db")
    dbname = os.getenv("POSTGRES_DB", "skyforge")
    user = os.getenv("POSTGRES_USER", "skyforge")
    password = os.getenv("POSTGRES_PASSWORD", "skyforge")
    connect_timeout = os.getenv("POSTGRES_CONNECT_TIMEOUT", "5")
    return f"host={host} dbname={dbname} user={user} password={password} connect_timeout={connect_timeout}"


def connect_db() -> psycopg2.extensions.connection:
    return psycopg2.connect(_get_dsn())


def wait_for_db(retries: int = 20, delay: int = 3) -> psycopg2.extensions.connection:
    for attempt in range(retries):
        try:
            conn: psycopg2.extensions.connection = connect_db()
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
            CREATE TABLE IF NOT EXISTS ah_sales (
                id              SERIAL PRIMARY KEY,
                item_name       TEXT NOT NULL,
                effective_price BIGINT NOT NULL,
                auction_id      TEXT,
                recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_ah_sales_lookup
                ON ah_sales (item_name, recorded_at)
        """)
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_ah_sales_auction_id
                ON ah_sales (auction_id)
                WHERE auction_id IS NOT NULL
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bazaar_snapshots (
                id            SERIAL PRIMARY KEY,
                item_name     TEXT NOT NULL,
                sell_price    BIGINT NOT NULL,
                sampled_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_bazaar_snapshots_lookup
                ON bazaar_snapshots (item_name, sampled_at)
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
        item_rows = typing.cast(list[ForgeItemRow], cur.fetchall())
        for name, duration in item_rows:
            items[name] = ForgeItemInfo({"Duration": duration, "Recipe": {}, "Requirements": {}})

        cur.execute("SELECT item_name, material, quantity FROM forge_recipes")
        recipe_rows = typing.cast(list[ForgeRecipeRow], cur.fetchall())
        for item_name, material, quantity in recipe_rows:
            items[item_name]["Recipe"][material] = quantity

        cur.execute("SELECT item_name, requirement, level FROM forge_requirements")
        requirement_rows = typing.cast(list[ForgeRequirementRow], cur.fetchall())
        for item_name, requirement, level in requirement_rows:
            items[item_name]["Requirements"][requirement] = level

    return items


def insert_ah_sales_with_price(conn: psycopg2.extensions.connection, sales: list[dict[str, int | str | None]]) -> int:
    inserted = 0

    with conn.cursor() as cur:
        for sale in sales:
            item_name_raw = sale.get("item_name")
            price_raw = sale.get("effective_price")
            auction_id_raw = sale.get("auction_id")

            if not isinstance(item_name_raw, str):
                continue
            if not isinstance(price_raw, int) or price_raw < 0:
                continue
            auction_id = auction_id_raw if isinstance(auction_id_raw, str) else None

            cur.execute(
                """
                INSERT INTO ah_sales (item_name, effective_price, auction_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (auction_id) WHERE auction_id IS NOT NULL DO NOTHING
                """,
                (item_name_raw, price_raw, auction_id),
            )

            if cur.rowcount > 0:
                inserted += 1

        # Keep eight days of history to support rolling seven-day analytics.
        cur.execute("DELETE FROM ah_sales WHERE recorded_at < NOW() - INTERVAL '8 days'")

    conn.commit()
    return inserted


def insert_bazaar_snapshots(conn: psycopg2.extensions.connection, snapshots: dict[str, int]) -> int:
    inserted = 0

    with conn.cursor() as cur:
        for item_name, sell_price_raw in snapshots.items():
            if sell_price_raw < 0:
                continue

            cur.execute(
                """
                INSERT INTO bazaar_snapshots (item_name, sell_price)
                VALUES (%s, %s)
                """,
                (item_name, sell_price_raw),
            )
            if cur.rowcount > 0:
                inserted += 1

        cur.execute("DELETE FROM bazaar_snapshots WHERE sampled_at < NOW() - INTERVAL '8 days'")

    conn.commit()
    return inserted


def read_market_summary_7d(
    conn: psycopg2.extensions.connection,
) -> dict[str, dict[str, dict[str, int | str | None]]]:
    """Read per-item 7-day market summaries for AH + Bazaar."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                item_name,
                MIN(effective_price) AS low,
                MAX(effective_price) AS high,
                CAST(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY effective_price) AS BIGINT) AS median,
                COUNT(*)::INT AS quantity,
                MIN(recorded_at)::TEXT AS oldest_recorded_at
            FROM ah_sales
            WHERE recorded_at > NOW() - INTERVAL '7 days'
            GROUP BY item_name
        """)
        rows = typing.cast(list[AHSalesSummaryRow], cur.fetchall())
        result: dict[str, dict[str, dict[str, int | str | None]]] = {}
        for item_name, low, high, median, quantity, oldest_recorded_at in rows:
            item_bucket = result.setdefault(item_name, {})
            item_bucket["AH"] = {
                "low": low,
                "high": high,
                "median": median,
                "quantity": quantity,
                "oldest_recorded_at": oldest_recorded_at,
            }

        cur.execute(
            """
            WITH base AS (
                SELECT
                    item_name,
                    sell_price,
                    sampled_at
                FROM bazaar_snapshots
                WHERE sampled_at > NOW() - INTERVAL '7 days'
            )
            SELECT
                item_name,
                MIN(sell_price) AS low,
                MAX(sell_price) AS high,
                CAST(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sell_price) AS BIGINT) AS median,
                COUNT(*)::INT AS quantity,
                MIN(sampled_at)::TEXT AS oldest_recorded_at
            FROM base
            GROUP BY item_name
            """
        )
        bazaar_rows = typing.cast(list[BazaarSummaryRow], cur.fetchall())
        for item_name, low, high, median, quantity, oldest_recorded_at in bazaar_rows:
            item_bucket = result.setdefault(item_name, {})
            item_bucket["Bazaar"] = {
                "low": low,
                "high": high,
                "median": median,
                "quantity": quantity,
                "oldest_recorded_at": oldest_recorded_at,
            }

        return result
