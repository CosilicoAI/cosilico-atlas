"""Storage backends for the law archive."""

from arch.storage.base import StorageBackend
from arch.storage.sqlite import SQLiteStorage

# PostgreSQL is optional - only import if installed
try:
    from arch.storage.postgres import PostgresStorage

    __all__ = ["StorageBackend", "SQLiteStorage", "PostgresStorage"]
except ImportError:
    __all__ = ["StorageBackend", "SQLiteStorage"]
