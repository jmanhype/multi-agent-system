"""SQL query execution with safety guardrails and timeout handling.

Implements FR-012 (parameterized queries), FR-013 (row limit enforcement), 
FR-014 (timeout handling).
"""

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import psycopg
from psycopg import sql


@dataclass
class SQLResult:
    """Result from SQL query execution."""
    rows: List[Dict[str, Any]]
    columns: List[str]
    row_count: int
    execution_time_seconds: float
    truncated: bool = False


class SQLExecutionError(Exception):
    """SQL execution failure."""
    def __init__(self, message: str, error_category: str):
        super().__init__(message)
        self.error_category = error_category


class SQLRunner:
    """Executes SQL queries with safety guardrails.
    
    Features:
    - Parameterized queries to prevent SQL injection (FR-012)
    - Configurable row limit enforcement (FR-013)
    - Timeout handling (FR-014)
    - Read-only transaction isolation
    """
    
    DEFAULT_ROW_LIMIT = 10000
    DEFAULT_TIMEOUT_SECONDS = 10.0
    
    def __init__(
        self,
        connection_string: str,
        row_limit: int = DEFAULT_ROW_LIMIT,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        """Initialize SQL runner.
        
        Args:
            connection_string: PostgreSQL connection string
            row_limit: Maximum rows to return (FR-013)
            timeout_seconds: Query timeout in seconds (FR-014)
        """
        self.connection_string = connection_string
        self.row_limit = row_limit
        self.timeout_seconds = timeout_seconds
    
    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> SQLResult:
        """Execute parameterized SQL query with safety guardrails.
        
        Args:
            query: SQL query with parameter placeholders (%(param_name)s format)
            params: Query parameters (FR-012: prevents SQL injection)
        
        Returns:
            SQLResult with rows, columns, metadata
        
        Raises:
            SQLExecutionError: Query failed (timeout, syntax, resource limit)
        """
        start_time = time.time()
        params = params or {}
        
        try:
            with psycopg.connect(self.connection_string) as conn:
                conn.execute("SET TRANSACTION READ ONLY")
                conn.execute(f"SET statement_timeout = {int(self.timeout_seconds * 1000)}")
                
                with conn.cursor() as cursor:
                    limited_query = self._apply_row_limit(query)
                    cursor.execute(limited_query, params)
                    
                    rows = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    
                    execution_time = time.time() - start_time
                    
                    truncated = len(rows) >= self.row_limit
                    
                    row_dicts = [dict(zip(columns, row)) for row in rows]
                    
                    return SQLResult(
                        rows=row_dicts,
                        columns=columns,
                        row_count=len(row_dicts),
                        execution_time_seconds=execution_time,
                        truncated=truncated,
                    )
        
        except psycopg.errors.QueryCanceled as e:
            raise SQLExecutionError(
                f"Query exceeded timeout of {self.timeout_seconds}s",
                error_category="timeout",
            ) from e
        
        except psycopg.errors.SyntaxError as e:
            raise SQLExecutionError(
                f"SQL syntax error: {str(e)}",
                error_category="sql_syntax",
            ) from e
        
        except psycopg.Error as e:
            raise SQLExecutionError(
                f"Database error: {str(e)}",
                error_category="resource_exhausted",
            ) from e
        
        except Exception as e:
            raise SQLExecutionError(
                f"Unexpected error: {str(e)}",
                error_category="tool_failure",
            ) from e
    
    def _apply_row_limit(self, query: str) -> str:
        """Enforce row limit on query (FR-013).
        
        Args:
            query: Original SQL query
        
        Returns:
            Query with LIMIT clause appended
        """
        query = query.strip().rstrip(';')
        
        if 'LIMIT' in query.upper():
            return query
        
        return f"{query} LIMIT {self.row_limit}"
    
    def get_schema_info(self, table_name: str) -> Dict[str, Any]:
        """Get table schema metadata.
        
        Args:
            table_name: Name of table to inspect
        
        Returns:
            Dict with columns, types, constraints
        
        Raises:
            SQLExecutionError: Schema query failed
        """
        schema_query = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = %(table_name)s
            ORDER BY ordinal_position
        """
        
        result = self.execute_query(schema_query, {"table_name": table_name})
        
        return {
            "table": table_name,
            "columns": result.rows,
            "column_count": result.row_count,
        }