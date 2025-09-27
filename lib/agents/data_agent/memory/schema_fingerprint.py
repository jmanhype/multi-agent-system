"""Schema fingerprinting for recipe matching.

Computes stable, consistent hashes of DataFrame schemas to enable
recipe retrieval based on data structure compatibility.
"""

import hashlib
from typing import Dict, List, Optional, Tuple
import pandas as pd


TYPE_NORMALIZATION = {
    'int64': 'integer',
    'int32': 'integer',
    'int16': 'integer',
    'int8': 'integer',
    'float64': 'float',
    'float32': 'float',
    'object': 'string',
    'string': 'string',
    'bool': 'boolean',
    'datetime64[ns]': 'timestamp',
    'datetime64[ns, UTC]': 'timestamp',
    'timedelta64[ns]': 'interval',
}


class SchemaFingerprinter:
    """Generate consistent fingerprints for database schemas.
    
    Fingerprints are stable SHA256 hashes of sorted column names and types,
    enabling recipe matching across structurally identical schemas.
    """
    
    def __init__(self, normalize_types: bool = True):
        """Initialize schema fingerprinter.
        
        Args:
            normalize_types: Whether to normalize types to canonical forms
                            (e.g., int64 -> integer, float32 -> float)
        """
        self.normalize_types = normalize_types
    
    def compute_fingerprint(
        self,
        columns: Dict[str, str],
        table_name: Optional[str] = None,
    ) -> str:
        """Compute SHA256 fingerprint for a schema.
        
        Args:
            columns: Dict mapping column names to data types
            table_name: Optional table name (not included in fingerprint)
        
        Returns:
            Hexadecimal SHA256 hash string
        
        Example:
            >>> fingerprinter = SchemaFingerprinter()
            >>> schema = {"user_id": "int64", "email": "string", "created_at": "timestamp"}
            >>> fingerprint = fingerprinter.compute_fingerprint(schema)
            >>> fingerprint
            'a3b1c5d7...'
        """
        if not columns:
            raise ValueError("Cannot compute fingerprint for empty schema")
        
        schema_items = []
        for col_name in sorted(columns.keys()):
            dtype = columns[col_name]
            
            if self.normalize_types:
                dtype = self._normalize_type(dtype)
            
            schema_items.append(f"{col_name}:{dtype}")
        
        schema_str = ",".join(schema_items)
        
        fingerprint = hashlib.sha256(schema_str.encode()).hexdigest()
        
        return fingerprint
    
    def compute_fingerprint_from_dataframe(self, df: pd.DataFrame) -> str:
        """Compute fingerprint directly from pandas DataFrame.
        
        Args:
            df: Input DataFrame
        
        Returns:
            Hexadecimal SHA256 hash string
        """
        columns = {str(col): str(df[col].dtype) for col in df.columns}
        return self.compute_fingerprint(columns)
    
    def compute_fingerprint_from_sql_result(
        self,
        cursor_description: List,
    ) -> str:
        """Compute fingerprint from SQL cursor description.
        
        Args:
            cursor_description: Result of cursor.description after query execution
                               (list of tuples: [(name, type_code, ...)])
        
        Returns:
            Hexadecimal SHA256 hash string
        """
        columns = {}
        for col_desc in cursor_description:
            col_name = col_desc[0]
            type_code = col_desc[1] if len(col_desc) > 1 else None
            
            type_str = self._sql_type_to_string(type_code)
            columns[col_name] = type_str
        
        return self.compute_fingerprint(columns)
    
    def _normalize_type(self, dtype: str) -> str:
        """Normalize data type to canonical form."""
        dtype_lower = dtype.lower()
        return TYPE_NORMALIZATION.get(dtype, dtype_lower)
    
    def _sql_type_to_string(self, type_code) -> str:
        """Convert SQL type code to string representation."""
        if type_code is None:
            return "unknown"
        
        type_map = {
            1: "integer",
            2: "integer",
            3: "integer",
            4: "float",
            5: "float",
            7: "timestamp",
            8: "string",
            9: "string",
            10: "string",
            11: "timestamp",
            12: "string",
        }
        
        return type_map.get(type_code, f"type_{type_code}")
    
    def schemas_match(self, fingerprint1: str, fingerprint2: str) -> bool:
        """Check if two fingerprints represent matching schemas."""
        return fingerprint1 == fingerprint2
    
    def get_schema_diff(
        self,
        schema1: Dict[str, str],
        schema2: Dict[str, str],
    ) -> Dict[str, any]:
        """Compare two schemas and return differences.
        
        Args:
            schema1: First schema (column name -> type)
            schema2: Second schema (column name -> type)
        
        Returns:
            Dict with keys: added_columns, removed_columns, changed_types
        """
        cols1 = set(schema1.keys())
        cols2 = set(schema2.keys())
        
        added = cols2 - cols1
        removed = cols1 - cols2
        common = cols1 & cols2
        
        changed = {}
        for col in common:
            type1 = self._normalize_type(schema1[col]) if self.normalize_types else schema1[col]
            type2 = self._normalize_type(schema2[col]) if self.normalize_types else schema2[col]
            
            if type1 != type2:
                changed[col] = {"from": type1, "to": type2}
        
        return {
            "added_columns": list(added),
            "removed_columns": list(removed),
            "changed_types": changed,
            "is_compatible": len(removed) == 0 and len(changed) == 0,
        }


def compute_schema_fingerprint(df: pd.DataFrame) -> str:
    """Generate SHA256 fingerprint of DataFrame schema.
    
    Creates a deterministic hash based on sorted column names and types.
    This enables recipe matching: two DataFrames with identical schemas
    will have the same fingerprint, allowing successful analysis patterns
    to be reused.
    
    Args:
        df: Input DataFrame
    
    Returns:
        SHA256 hash (64 hex characters) of schema structure
        
    Example:
        >>> df = pd.DataFrame({"sales": [100, 200], "region": ["AZ", "CA"]})
        >>> fp = compute_schema_fingerprint(df)
        >>> len(fp)
        64
    """
    fingerprinter = SchemaFingerprinter(normalize_types=True)
    return fingerprinter.compute_fingerprint_from_dataframe(df)


def schema_compatible(fp1: str, fp2: str) -> bool:
    """Check if two schema fingerprints are compatible.
    
    Args:
        fp1: First schema fingerprint
        fp2: Second schema fingerprint
    
    Returns:
        True if fingerprints match (schemas are identical)
    """
    return fp1 == fp2


def get_schema_summary(df: pd.DataFrame) -> List[Tuple[str, str]]:
    """Extract human-readable schema summary.
    
    Args:
        df: Input DataFrame
    
    Returns:
        List of (column_name, dtype) tuples sorted by column name
        
    Example:
        >>> df = pd.DataFrame({"sales": [100], "region": ["AZ"]})
        >>> get_schema_summary(df)
        [('region', 'object'), ('sales', 'int64')]
    """
    return [(col, str(df[col].dtype)) for col in sorted(df.columns)]