"""Unit tests for database connection utilities."""

import pytest
import tempfile
from pathlib import Path

from lib.agents.data_agent.db.connection import DatabaseConnection


class TestDatabaseConnection:
    """Tests for DatabaseConnection utility."""
    
    def test_sqlite_connection_context_manager(self):
        """DatabaseConnection must provide working SQLite context manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            db = DatabaseConnection(db_path=db_path)
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("CREATE TABLE test (id INTEGER, value TEXT)")
                cursor.execute("INSERT INTO test VALUES (1, 'hello')")
            
            # Verify data persisted
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM test")
                rows = cursor.fetchall()
                assert len(rows) == 1
                assert rows[0] == (1, "hello")
    
    def test_run_migrations_creates_tracking_table(self):
        """DatabaseConnection must create schema_migrations tracking table."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            db = DatabaseConnection(db_path=db_path)
            
            # Create empty migrations dir
            migrations_dir = Path(tmpdir) / "migrations"
            migrations_dir.mkdir()
            
            db.run_migrations(str(migrations_dir))
            
            # Verify tracking table exists
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
                )
                assert cursor.fetchone() is not None
    
    def test_run_migrations_applies_pending_migrations(self):
        """DatabaseConnection must apply pending migrations in order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            db = DatabaseConnection(db_path=db_path)
            
            # Create migrations
            migrations_dir = Path(tmpdir) / "migrations"
            migrations_dir.mkdir()
            
            (migrations_dir / "001_create_users.sql").write_text(
                "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)"
            )
            (migrations_dir / "002_create_posts.sql").write_text(
                "CREATE TABLE posts (id INTEGER PRIMARY KEY, user_id INTEGER, content TEXT)"
            )
            
            db.run_migrations(str(migrations_dir))
            
            # Verify both tables exist
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                )
                tables = [row[0] for row in cursor.fetchall()]
                assert "users" in tables
                assert "posts" in tables
                assert "schema_migrations" in tables
    
    def test_run_migrations_skips_applied_migrations(self):
        """DatabaseConnection must not re-apply already applied migrations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            db = DatabaseConnection(db_path=db_path)
            
            migrations_dir = Path(tmpdir) / "migrations"
            migrations_dir.mkdir()
            
            (migrations_dir / "001_create_test.sql").write_text(
                "CREATE TABLE test (id INTEGER PRIMARY KEY)"
            )
            
            # Apply first time
            db.run_migrations(str(migrations_dir))
            
            # Apply again - should not error
            db.run_migrations(str(migrations_dir))
            
            # Verify only one migration recorded
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM schema_migrations")
                count = cursor.fetchone()[0]
                assert count == 1
    
    def test_check_connection_returns_true_when_working(self):
        """DatabaseConnection must return True for working connection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test.db")
            db = DatabaseConnection(db_path=db_path)
            
            assert db.check_connection() is True
    
    def test_check_connection_returns_false_on_error(self):
        """DatabaseConnection must return False for failed connection."""
        # Invalid db path that will fail
        db = DatabaseConnection(db_path="/invalid/path/that/does/not/exist/test.db")
        
        # check_connection should handle error gracefully
        assert db.check_connection() is False
    
    def test_reset_database_deletes_sqlite_file(self):
        """DatabaseConnection must delete SQLite file on reset."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = DatabaseConnection(db_path=str(db_path))
            
            # Create database
            with db.get_connection() as conn:
                conn.execute("CREATE TABLE test (id INTEGER)")
            
            assert db_path.exists()
            
            # Reset
            db.reset_database()
            
            assert not db_path.exists()
    
    def test_postgres_requires_connection_string(self):
        """DatabaseConnection must require connection_string for Postgres."""
        with pytest.raises(ValueError, match="Postgres requires connection_string"):
            DatabaseConnection(db_type="postgres")
    
    def test_unsupported_db_type_raises_error(self):
        """DatabaseConnection must raise error for unsupported database type."""
        db = DatabaseConnection(db_type="mysql")
        
        with pytest.raises(ValueError, match="Unsupported database type"):
            with db.get_connection():
                pass