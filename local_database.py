"""SQLite persistence for local application queues and loan statuses."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator

from config import get_settings

VALID_STATUSES = {"new", "approved", "escalated"}


class LoanDatabase:
    def __init__(self, database_path: Path | str | None = None):
        self.path = Path(database_path or get_settings().sqlite_database_path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS loan_applications (
                    customer_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'new'
                        CHECK(status IN ('new', 'approved', 'escalated')),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def add_application(self, customer_id: str, status: str = "new") -> None:
        if status not in VALID_STATUSES:
            raise ValueError(f"Unsupported status: {status}")
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO loan_applications(customer_id, status)
                VALUES (?, ?)
                ON CONFLICT(customer_id) DO NOTHING
                """,
                (customer_id, status),
            )

    def sync_customers(self, customer_ids: list[str]) -> None:
        for customer_id in customer_ids:
            self.add_application(customer_id)

    def exists(self, customer_id: str) -> bool:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM loan_applications WHERE customer_id = ?", (customer_id,)
            ).fetchone()
        return row is not None

    def list_by_status(self, status: str) -> list[str]:
        if status not in VALID_STATUSES:
            raise ValueError(f"Unsupported status: {status}")
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT customer_id FROM loan_applications WHERE status = ? ORDER BY created_at, customer_id",
                (status,),
            ).fetchall()
        return [row["customer_id"] for row in rows]

    def set_status(self, customer_id: str, status: str) -> None:
        if status not in VALID_STATUSES:
            raise ValueError(f"Unsupported status: {status}")
        with self.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE loan_applications
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE customer_id = ?
                """,
                (status, customer_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(customer_id)
