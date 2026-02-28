import os
import time

import psycopg2
import psycopg2.extensions

from common.types import ForgeItemInfo


def _get_dsn() -> str:
    host = os.getenv("POSTGRES_HOST", "db")
    dbname = os.getenv("POSTGRES_DB", "skyforge")
    user = os.getenv("POSTGRES_USER", "skyforge")
    password = os.getenv("POSTGRES_PASSWORD", "skyforge")
    return f"host={host} dbname={dbname} user={user} password={password}"


def wait_for_db(retries: int = 10, delay: int = 3) -> psycopg2.extensions.connection:
    dsn = _get_dsn()
    for attempt in range(retries):
        try:
            conn: psycopg2.extensions.connection = psycopg2.connect(dsn)
            return conn
        except psycopg2.OperationalError as e:
            if attempt < retries - 1:
                print(f"[db] Not ready yet (attempt {attempt + 1}/{retries}), retrying in {delay}s...")
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
    conn.commit()


def upsert_forge_items(
    conn: psycopg2.extensions.connection,
    items: dict[str, ForgeItemInfo],
) -> None:
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
