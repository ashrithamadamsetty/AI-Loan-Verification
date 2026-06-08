"""Initialize local storage and SQLite, optionally registering existing customer folders."""

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import get_settings
from local_database import LoanDatabase
from local_storage import LocalStorage


def main() -> None:
    settings = get_settings()
    storage = LocalStorage(settings.local_storage_path)
    database = LoanDatabase(settings.sqlite_database_path)
    customers = storage.list_customer_ids()
    database.sync_customers(customers)
    print(f"Local storage: {storage.root}")
    print(f"SQLite database: {database.path}")
    print(f"Registered customer folders: {len(customers)}")


if __name__ == "__main__":
    main()
