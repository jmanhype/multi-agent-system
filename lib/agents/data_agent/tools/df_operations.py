"""DataFrame operations for data transformation and analysis.

Implements FR-015 (DataFrame operations: filter, aggregate, join, transform).
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
import pandas as pd


@dataclass
class DataFrameResult:
    """Result from DataFrame operation."""
    df: pd.DataFrame
    operation: str
    row_count: int
    column_count: int
    execution_time_seconds: float
    metadata: Dict[str, Any]


class DataFrameOperationError(Exception):
    """DataFrame operation failure."""
    def __init__(self, message: str, error_category: str):
        super().__init__(message)
        self.error_category = error_category


class DataFrameOperations:
    """DataFrame transformation operations.
    
    Provides:
    - filter: Row filtering with predicate expressions
    - aggregate: Groupby and aggregation operations
    - join: DataFrame merge operations
    - transform: Column transformations and calculations
    """
    
    def __init__(self, max_memory_mb: int = 1024):
        """Initialize DataFrame operations.
        
        Args:
            max_memory_mb: Maximum memory usage for operations
        """
        self.max_memory_mb = max_memory_mb
    
    def filter(
        self,
        df: pd.DataFrame,
        predicate: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """Filter DataFrame rows by predicate.
        
        Args:
            df: Input DataFrame
            predicate: Pandas query string (e.g., "age > 30 and city == @target_city")
            variables: Variables for @ references in predicate
        
        Returns:
            Filtered DataFrame
        
        Raises:
            DataFrameOperationError: Filter failed
        
        Examples:
            >>> df = pd.DataFrame({"age": [25, 35, 45], "city": ["NY", "LA", "NY"]})
            >>> ops.filter(df, "age > 30 and city == 'NY'")
        """
        try:
            variables = variables or {}
            result = df.query(predicate, local_dict=variables)
            return result
        
        except pd.errors.UndefinedVariableError as e:
            raise DataFrameOperationError(
                f"Undefined variable in predicate: {str(e)}",
                error_category="missing_column",
            ) from e
        
        except Exception as e:
            raise DataFrameOperationError(
                f"Filter operation failed: {str(e)}",
                error_category="type_mismatch",
            ) from e
    
    def aggregate(
        self,
        df: pd.DataFrame,
        group_by: List[str],
        aggregations: Dict[str, Union[str, List[str]]],
    ) -> pd.DataFrame:
        """Aggregate DataFrame by groups.
        
        Args:
            df: Input DataFrame
            group_by: Columns to group by
            aggregations: Dict mapping column -> aggregation function(s)
                         (e.g., {"sales": "sum", "price": ["mean", "max"]})
        
        Returns:
            Aggregated DataFrame
        
        Raises:
            DataFrameOperationError: Aggregation failed
        
        Examples:
            >>> df = pd.DataFrame({
            ...     "region": ["A", "A", "B"],
            ...     "sales": [100, 200, 150],
            ...     "price": [10, 20, 15]
            ... })
            >>> ops.aggregate(df, ["region"], {"sales": "sum", "price": "mean"})
        """
        try:
            for col in group_by:
                if col not in df.columns:
                    raise DataFrameOperationError(
                        f"Group by column '{col}' not found in DataFrame",
                        error_category="missing_column",
                    )
            
            result = df.groupby(group_by).agg(aggregations).reset_index()
            return result
        
        except KeyError as e:
            raise DataFrameOperationError(
                f"Column not found: {str(e)}",
                error_category="missing_column",
            ) from e
        
        except Exception as e:
            raise DataFrameOperationError(
                f"Aggregation failed: {str(e)}",
                error_category="type_mismatch",
            ) from e
    
    def join(
        self,
        left: pd.DataFrame,
        right: pd.DataFrame,
        on: Optional[Union[str, List[str]]] = None,
        how: str = "inner",
        left_on: Optional[Union[str, List[str]]] = None,
        right_on: Optional[Union[str, List[str]]] = None,
    ) -> pd.DataFrame:
        """Join two DataFrames.
        
        Args:
            left: Left DataFrame
            right: Right DataFrame
            on: Column(s) to join on (if same name in both)
            how: Join type ("inner", "left", "right", "outer")
            left_on: Column(s) in left DataFrame to join on
            right_on: Column(s) in right DataFrame to join on
        
        Returns:
            Joined DataFrame
        
        Raises:
            DataFrameOperationError: Join failed
        
        Examples:
            >>> left = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
            >>> right = pd.DataFrame({"id": [1, 2], "value": [10, 20]})
            >>> ops.join(left, right, on="id")
        """
        try:
            if on is not None:
                result = left.merge(right, on=on, how=how)
            elif left_on is not None and right_on is not None:
                result = left.merge(right, left_on=left_on, right_on=right_on, how=how)
            else:
                raise DataFrameOperationError(
                    "Must specify either 'on' or both 'left_on' and 'right_on'",
                    error_category="type_mismatch",
                )
            
            return result
        
        except KeyError as e:
            raise DataFrameOperationError(
                f"Join column not found: {str(e)}",
                error_category="missing_column",
            ) from e
        
        except Exception as e:
            raise DataFrameOperationError(
                f"Join operation failed: {str(e)}",
                error_category="type_mismatch",
            ) from e
    
    def transform(
        self,
        df: pd.DataFrame,
        transformations: Dict[str, str],
    ) -> pd.DataFrame:
        """Apply column transformations.
        
        Args:
            df: Input DataFrame
            transformations: Dict mapping new_column -> expression
                           (e.g., {"total": "quantity * price", "discount_pct": "discount / 100"})
        
        Returns:
            DataFrame with new/updated columns
        
        Raises:
            DataFrameOperationError: Transformation failed
        
        Examples:
            >>> df = pd.DataFrame({"quantity": [10, 20], "price": [5, 10]})
            >>> ops.transform(df, {"total": "quantity * price"})
        """
        try:
            result = df.copy()
            
            for new_col, expr in transformations.items():
                result[new_col] = result.eval(expr)
            
            return result
        
        except pd.errors.UndefinedVariableError as e:
            raise DataFrameOperationError(
                f"Undefined column in expression: {str(e)}",
                error_category="missing_column",
            ) from e
        
        except Exception as e:
            raise DataFrameOperationError(
                f"Transform operation failed: {str(e)}",
                error_category="type_mismatch",
            ) from e
    
    def sort(
        self,
        df: pd.DataFrame,
        by: Union[str, List[str]],
        ascending: Union[bool, List[bool]] = True,
    ) -> pd.DataFrame:
        """Sort DataFrame by columns.
        
        Args:
            df: Input DataFrame
            by: Column(s) to sort by
            ascending: Sort order (True for ascending, False for descending)
        
        Returns:
            Sorted DataFrame
        
        Raises:
            DataFrameOperationError: Sort failed
        """
        try:
            result = df.sort_values(by=by, ascending=ascending).reset_index(drop=True)
            return result
        
        except KeyError as e:
            raise DataFrameOperationError(
                f"Sort column not found: {str(e)}",
                error_category="missing_column",
            ) from e
        
        except Exception as e:
            raise DataFrameOperationError(
                f"Sort operation failed: {str(e)}",
                error_category="type_mismatch",
            ) from e
    
    def select(
        self,
        df: pd.DataFrame,
        columns: List[str],
    ) -> pd.DataFrame:
        """Select subset of columns.
        
        Args:
            df: Input DataFrame
            columns: Columns to select
        
        Returns:
            DataFrame with selected columns
        
        Raises:
            DataFrameOperationError: Selection failed
        """
        try:
            result = df[columns].copy()
            return result
        
        except KeyError as e:
            raise DataFrameOperationError(
                f"Column not found: {str(e)}",
                error_category="missing_column",
            ) from e