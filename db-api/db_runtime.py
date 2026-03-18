import logging
import typing
from datetime import datetime
from pathlib import Path

import db
import psycopg2
from forge_data_loader import load_forge_items

T = typing.TypeVar("T")


class DBUnavailableError(Exception):
    pass


class DBRuntime:
    def __init__(self, logger: logging.Logger, forge_data_path: Path) -> None:
        self._logger = logger
        self._forge_data_path = forge_data_path
        self.last_scraped_at: datetime | None = None
        self._conn = self._connect_db()

    def _connect_db(self) -> psycopg2.extensions.connection:
        self._logger.info("Waiting for database...")
        connection = db.wait_for_db()
        db.init_schema(connection)
        items, last_updated = load_forge_items(self._forge_data_path, self._logger)
        db.upsert_forge_items(connection, items)
        self.last_scraped_at = last_updated or datetime.now()
        self._logger.info(f"Loaded {len(items)} forge items from {self._forge_data_path.name}")
        self._logger.info("Database ready.")
        return connection

    def _reconnect_db(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
        self._conn = self._connect_db()

    def _run_db_op(
        self, operation: typing.Callable[[psycopg2.extensions.connection], T], *, retry_on_disconnect: bool
    ) -> T:
        for attempt in range(2):
            try:
                if self._conn.closed:
                    raise psycopg2.InterfaceError("Database connection is closed")
                return operation(self._conn)
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == 1 or not retry_on_disconnect:
                    raise
                self._logger.warning(f"Database connection lost ({e}). Reconnecting and retrying request...")
                self._reconnect_db()

        raise RuntimeError("Unreachable")

    def run_read(self, operation: typing.Callable[[psycopg2.extensions.connection], T]) -> T:
        try:
            return self._run_db_op(operation, retry_on_disconnect=True)
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            self._logger.warning(f"DB read failed: {e}")
            raise DBUnavailableError from e

    def run_write(self, operation: typing.Callable[[psycopg2.extensions.connection], T]) -> T:
        try:
            return self._run_db_op(operation, retry_on_disconnect=False)
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            self._reconnect_db()
            self._logger.warning(f"DB write failed: {e}")
            raise DBUnavailableError from e
