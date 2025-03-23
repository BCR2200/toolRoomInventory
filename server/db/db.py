from enum import Enum
from os import PathLike
import sqlite3
from typing import List, Self, Optional, ClassVar
from threading import Lock

from server.db.meta_props import MetaProps


class Params(Enum):
    DB_VERSION = 'db_version'


class DB:
    _MIGRATIONS: List[str] = [
        # Create users table
        '''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            name TEXT NOT NULL,
            is_admin BOOLEAN NOT NULL DEFAULT 0,
            is_user BOOLEAN NOT NULL DEFAULT 1
        )''',
        
        # Create inventory table
        '''CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            picture TEXT,
            signed_out BOOLEAN NOT NULL DEFAULT 0,
            holder_id INTEGER,
            signed_out_since TEXT,
            FOREIGN KEY (holder_id) REFERENCES users(id)
        )'''
    ]
    VERSION = len(_MIGRATIONS)
    _cached_db_version: ClassVar[Optional[int]] = None
    _version_lock: ClassVar[Lock] = Lock()
    _migration_lock: ClassVar[Lock] = Lock()  # Singleton lock for migrations

    def __init__(self, filename: str | bytes | PathLike[str], auto_migrate=False):
        """Initialize database connection and handle migrations if needed."""
        self.filename = filename
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
        
        # Connect and check migrations during initialization
        self.connect()
        try:
            db_version = self._get_db_version()
            if db_version != self.VERSION:
                if auto_migrate:
                    # Acquire migration lock before attempting migration
                    with DB._migration_lock:
                        # Double-check pattern: Re-check version after acquiring lock in case another thread migrated
                        db_version = self._get_db_version()
                        if db_version != self.VERSION:
                            self.migrate()
                else:
                    raise RuntimeError(
                        f'Database version {db_version} does not match required version {self.VERSION}. '
                        'Must run with auto_migrate=True.'
                    )
        finally:
            self.close()

    def __enter__(self) -> Self:
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self):
        """Create a new connection with appropriate settings."""
        self.conn = sqlite3.connect(self.filename)
        self.cursor = self.conn.cursor()
        
        # Set pragmas for better performance and safety
        for pragma in [
            'PRAGMA journal_mode=WAL',          # Allow concurrent reads
            'PRAGMA busy_timeout=5000',         # Wait up to 5s if db is locked
            'PRAGMA foreign_keys=ON',           # Enforce foreign key constraints
            'PRAGMA synchronous=NORMAL',        # Good balance of safety and speed
            'PRAGMA recursive_triggers=ON'      # Enable recursive triggers
        ]:
            self.cursor.execute(pragma)

    def close(self):
        """Close the database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.commit()
            self.conn.close()
            self.conn = None
            self.cursor = None

    def self_test(self):
        """Test the database connection."""
        self.cursor.execute('SELECT 1')
        if self.cursor.fetchone()[0] != 1:
            raise RuntimeError('Self-test failed: Unexpected database response.')

    def _get_db_version(self) -> int:
        """Get the current database version, using cached value if available."""
        # Check if we have a cached version
        if self._cached_db_version is not None:
            return self._cached_db_version

        # If not, we need to read from the database
        with self._version_lock:
            # Double-check pattern in case another thread got here first
            if self._cached_db_version is not None:
                return self._cached_db_version

            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS db_meta_props(
                name TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            ''')

            db_version = self.cursor.execute('''
            SELECT value FROM db_meta_props WHERE name = ?
            ''', [MetaProps.DB_VERSION.value]).fetchone()
            
            if db_version is None:
                DB._cached_db_version = 0
            else:
                DB._cached_db_version = int(db_version[0])
            
            return DB._cached_db_version

    def migrate(self):
        """Apply any pending migrations."""
        self.cursor.execute('BEGIN EXCLUSIVE TRANSACTION;')
        try:
            from_ver = self._get_db_version()
            to_ver = self.VERSION
            migrations = self._MIGRATIONS[from_ver:to_ver]
            
            for i, migration in enumerate(migrations, start=from_ver):
                print('--------------')
                print(f'Applying migration {i}: {migration}')
                self.cursor.execute(migration)
                print('--------------')
            
            self.cursor.execute(
                'INSERT OR REPLACE INTO db_meta_props(name, value) VALUES(?, ?)',
                [MetaProps.DB_VERSION.value, to_ver]
            )
            # Update the cached version after successful migration
            with self._version_lock:
                DB._cached_db_version = to_ver
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    @classmethod
    def reset_version_cache(cls):
        """Reset the cached database version. Useful for testing."""
        with cls._version_lock:
            cls._cached_db_version = None
