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
        self.last_updated: datetime | None = None
        self._initialize_db()

    def _initialize_db(self) -> None:
        self._logger.info("Waiting for database...")
        connection = db.wait_for_db()
        try:
            db.init_schema(connection)
            items, last_updated = load_forge_items(self._forge_data_path, self._logger)
            db.upsert_forge_items(connection, items)
            self.last_updated = last_updated or datetime.now()
            self._logger.info(f"Loaded {len(items)} forge items from {self._forge_data_path.name}")
            self._logger.info("Database ready.")
        finally:
            try:
                connection.close()
            except Exception:
                pass

    def _run_db_op(
        self,
        operation: typing.Callable[..., T],
        *args: typing.Any,
        retry_on_disconnect: bool,
    ) -> T:
        max_attempts = 2 if retry_on_disconnect else 1
        for attempt in range(max_attempts):
            connection: psycopg2.extensions.connection | None = None
            try:
                connection = db.connect_db()
                return operation(connection, *args)
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt == max_attempts - 1:
                    raise
                self._logger.warning(f"Database connection lost ({e}). Retrying request...")
            finally:
                if connection is not None:
                    try:
                        connection.close()
                    except Exception:
                        pass

        raise RuntimeError("Unreachable")

    def run(
        self,
        operation: typing.Callable[..., T],
        *args: typing.Any,
        retry_on_disconnect: bool,
    ) -> T:
        try:
            return self._run_db_op(operation, *args, retry_on_disconnect=retry_on_disconnect)
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            self._logger.warning(f"DB operation failed: {e}")
            raise DBUnavailableError from e
