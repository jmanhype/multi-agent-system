"""Data profiling tool for schema discovery and quality assessment.

Discovers schema metadata and computes data quality metrics.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np

from ..memory.schema_fingerprint import SchemaFingerprinter


@dataclass
class ColumnProfile:
    """Profile for a single column."""
    name: str
    dtype: str
    null_count: int
    null_percentage: float
    unique_count: int
    unique_percentage: float
    sample_values: List[Any]
    
    numeric_stats: Optional[Dict[str, float]] = None
    string_stats: Optional[Dict[str, Any]] = None
    categorical_stats: Optional[Dict[str, Any]] = None


@dataclass
class DataProfile:
    """Complete data profile."""
    row_count: int
    column_count: int
    memory_usage_bytes: int
    columns: List[ColumnProfile]
    quality_score: float
    warnings: List[str]


class DataProfiler:
    """Profile DataFrames and tables for schema and quality.
    
    Features:
    - Schema discovery (column names, types, constraints)
    - Data quality metrics (nulls, uniqueness, distributions)
    - Statistical summaries (numeric columns)
    - Categorical analysis (value frequencies)
    """
    
    def __init__(
        self,
        sample_size: int = 10,
        quality_thresholds: Optional[Dict[str, float]] = None,
    ):
        """Initialize data profiler.
        
        Args:
            sample_size: Number of sample values to include per column
            quality_thresholds: Thresholds for quality warnings
                               (e.g., {"max_null_pct": 0.1, "min_unique_pct": 0.01})
        """
        self.sample_size = sample_size
        self.quality_thresholds = quality_thresholds or {
            "max_null_pct": 0.1,
            "min_unique_pct": 0.001,
        }
    
    def profile_dataframe(self, df: pd.DataFrame) -> DataProfile:
        """Generate comprehensive profile for DataFrame.
        
        Args:
            df: Input DataFrame
        
        Returns:
            DataProfile with schema, statistics, and quality metrics
        """
        row_count = len(df)
        column_count = len(df.columns)
        memory_usage = df.memory_usage(deep=True).sum()
        
        columns = []
        warnings = []
        
        for col in df.columns:
            col_profile = self._profile_column(df, col, row_count)
            columns.append(col_profile)
            
            if col_profile.null_percentage > self.quality_thresholds["max_null_pct"]:
                warnings.append(
                    f"Column '{col}' has {col_profile.null_percentage:.1%} null values "
                    f"(threshold: {self.quality_thresholds['max_null_pct']:.1%})"
                )
            
            if col_profile.unique_percentage < self.quality_thresholds["min_unique_pct"]:
                warnings.append(
                    f"Column '{col}' has low uniqueness {col_profile.unique_percentage:.2%} "
                    f"(threshold: {self.quality_thresholds['min_unique_pct']:.2%})"
                )
        
        quality_score = self._compute_quality_score(columns, row_count)
        
        return DataProfile(
            row_count=row_count,
            column_count=column_count,
            memory_usage_bytes=int(memory_usage),
            columns=columns,
            quality_score=quality_score,
            warnings=warnings,
        )
    
    def _profile_column(
        self,
        df: pd.DataFrame,
        col: str,
        row_count: int,
    ) -> ColumnProfile:
        """Profile a single column."""
        series = df[col]
        
        null_count = int(series.isnull().sum())
        null_pct = null_count / row_count if row_count > 0 else 0.0
        
        unique_count = int(series.nunique())
        unique_pct = unique_count / row_count if row_count > 0 else 0.0
        
        sample_values = series.dropna().head(self.sample_size).tolist()
        
        dtype = str(series.dtype)
        
        numeric_stats = None
        string_stats = None
        categorical_stats = None
        
        if pd.api.types.is_numeric_dtype(series):
            numeric_stats = self._compute_numeric_stats(series)
        
        elif pd.api.types.is_string_dtype(series) or series.dtype == object:
            string_stats = self._compute_string_stats(series)
            
            if unique_count <= 50:
                categorical_stats = self._compute_categorical_stats(series)
        
        return ColumnProfile(
            name=col,
            dtype=dtype,
            null_count=null_count,
            null_percentage=null_pct,
            unique_count=unique_count,
            unique_percentage=unique_pct,
            sample_values=sample_values,
            numeric_stats=numeric_stats,
            string_stats=string_stats,
            categorical_stats=categorical_stats,
        )
    
    def _compute_numeric_stats(self, series: pd.Series) -> Dict[str, float]:
        """Compute statistics for numeric column."""
        clean_series = series.dropna()
        
        if len(clean_series) == 0:
            return {
                "min": None,
                "max": None,
                "mean": None,
                "median": None,
                "std": None,
                "q25": None,
                "q75": None,
            }
        
        return {
            "min": float(clean_series.min()),
            "max": float(clean_series.max()),
            "mean": float(clean_series.mean()),
            "median": float(clean_series.median()),
            "std": float(clean_series.std()),
            "q25": float(clean_series.quantile(0.25)),
            "q75": float(clean_series.quantile(0.75)),
        }
    
    def _compute_string_stats(self, series: pd.Series) -> Dict[str, Any]:
        """Compute statistics for string column."""
        clean_series = series.dropna()
        
        if len(clean_series) == 0:
            return {
                "min_length": None,
                "max_length": None,
                "mean_length": None,
            }
        
        lengths = clean_series.astype(str).str.len()
        
        return {
            "min_length": int(lengths.min()),
            "max_length": int(lengths.max()),
            "mean_length": float(lengths.mean()),
        }
    
    def _compute_categorical_stats(self, series: pd.Series) -> Dict[str, Any]:
        """Compute statistics for categorical column."""
        value_counts = series.value_counts()
        
        top_values = value_counts.head(10).to_dict()
        
        return {
            "top_values": {str(k): int(v) for k, v in top_values.items()},
            "top_value": str(value_counts.index[0]) if len(value_counts) > 0 else None,
            "top_value_count": int(value_counts.iloc[0]) if len(value_counts) > 0 else 0,
        }
    
    def _compute_quality_score(
        self,
        columns: List[ColumnProfile],
        row_count: int,
    ) -> float:
        """Compute overall data quality score (0.0 to 1.0).
        
        Quality factors:
        - Completeness (1 - avg null percentage)
        - Uniqueness (avg unique percentage for non-PK columns)
        """
        if not columns:
            return 0.0
        
        avg_null_pct = np.mean([col.null_percentage for col in columns])
        completeness = 1.0 - avg_null_pct
        
        non_constant_cols = [col for col in columns if col.unique_count > 1]
        if non_constant_cols:
            avg_unique_pct = np.mean([col.unique_percentage for col in non_constant_cols])
            uniqueness = min(avg_unique_pct * 10, 1.0)
        else:
            uniqueness = 0.0
        
        quality_score = 0.7 * completeness + 0.3 * uniqueness
        
        return float(quality_score)
    
    def get_schema_fingerprint(self, df: pd.DataFrame) -> str:
        """Generate schema fingerprint for recipe matching.
        
        Args:
            df: Input DataFrame
        
        Returns:
            SHA256 hash of sorted column names and types
        """
        fingerprinter = SchemaFingerprinter(normalize_types=True)
        return fingerprinter.compute_fingerprint_from_dataframe(df)