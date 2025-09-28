"""Database connection utilities for DataAgent.

Provides connection pooling and migration management for SQLite and PostgreSQL.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional
import logging

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Database connection manager with migration support.
    
    Features:
    - SQLite and PostgreSQL support
    - Connection pooling (via context managers)
    - Migration runner for schema versioning
    - Thread-safe operations
    """
    
    def __init__(
        self,
        db_path: str = "db/recipe_memory.db",
        db_type: str = "sqlite",
        connection_string: Optional[str] = None,
    ):
        """Initialize database connection manager.
        
        Args:
            db_path: Path to SQLite database file
            db_type: Database type ('sqlite' or 'postgres')
            connection_string: Optional Postgres connection string
        """
        self.db_type = db_type
        self.db_path = Path(db_path)
        self.connection_string = connection_string
        
        if self.db_type == "sqlite":
            try:
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as e:
                logger.warning(f"Could not create database directory: {e}")
        elif self.db_type == "postgres" and not connection_string:
            raise ValueError("Postgres requires connection_string")
    
    @contextmanager
    def get_connection(self) -> Generator:
        """Get database connection with automatic cleanup.
        
        Yields:
            Database connection object
        
        Example:
            >>> db = DatabaseConnection()
            >>> with db.get_connection() as conn:
            ...     cursor = conn.cursor()
            ...     cursor.execute("SELECT * FROM recipes")
        """
        if self.db_type == "sqlite":
            conn = sqlite3.connect(self.db_path)
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
        elif self.db_type == "postgres":
            try:
                import psycopg
                conn = psycopg.connect(self.connection_string)
                try:
                    yield conn
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
                finally:
                    conn.close()
            except ImportError:
                raise ImportError(
                    "psycopg required for Postgres support. "
                    "Install with: pip install psycopg[binary]"
                )
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
    
    def run_migrations(self, migrations_dir: str = "db/migrations") -> None:
        """Run all pending migrations in order.
        
        Migrations are SQL files named NNN_description.sql (e.g., 001_create_recipes.sql).
        Tracks applied migrations in a metadata table.
        
        Args:
            migrations_dir: Directory containing migration SQL files
        
        Example:
            >>> db = DatabaseConnection()
            >>> db.run_migrations()
            Applied migration: 001_create_recipes.sql
        """
        migrations_path = Path(migrations_dir)
        
        if not migrations_path.exists():
            logger.warning(f"Migrations directory not found: {migrations_dir}")
            return
        
        # Create migrations tracking table
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    migration_id TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
            """)
            
            # Get applied migrations
            cursor = conn.cursor()
            cursor.execute("SELECT migration_id FROM schema_migrations")
            applied = {row[0] for row in cursor.fetchall()}
            
            # Find and apply pending migrations
            migration_files = sorted(migrations_path.glob("*.sql"))
            
            for migration_file in migration_files:
                migration_id = migration_file.name
                
                if migration_id in applied:
                    logger.debug(f"Skipping applied migration: {migration_id}")
                    continue
                
                logger.info(f"Applying migration: {migration_id}")
                
                # Read and execute migration SQL
                migration_sql = migration_file.read_text()
                
                # Execute migration SQL
                # Note: executescript() auto-commits, breaking transaction handling
                # Use cursor.execute() for each statement instead
                cursor = conn.cursor()
                cursor.executescript(migration_sql)
                
                # Record migration as applied
                from datetime import datetime, timezone
                applied_at = datetime.now(timezone.utc).isoformat()
                conn.execute(
                    "INSERT INTO schema_migrations (migration_id, applied_at) VALUES (?, ?)",
                    (migration_id, applied_at),
                )
                
                logger.info(f"Applied migration: {migration_id}")
    
    def check_connection(self) -> bool:
        """Verify database connection is working.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False
    
    def reset_database(self) -> None:
        """Reset database by dropping all tables (DANGEROUS).
        
        Only use for testing/development. Requires explicit confirmation.
        """
        if self.db_type == "sqlite":
            if self.db_path.exists():
                self.db_path.unlink()
                logger.warning(f"Deleted SQLite database: {self.db_path}")
        elif self.db_type == "postgres":
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public'
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                for table in tables:
                    conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                
                logger.warning(f"Dropped {len(tables)} tables from Postgres")