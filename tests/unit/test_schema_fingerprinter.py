"""Unit tests for SchemaFingerprinter class.

Tests enhanced fingerprinting functionality including type normalization,
schema diff, and SQL cursor support.
"""

import pandas as pd
import pytest

from lib.agents.data_agent.memory.schema_fingerprint import SchemaFingerprinter, TYPE_NORMALIZATION


class TestSchemaFingerprinterClass:
    """Test SchemaFingerprinter class methods."""
    
    def test_type_normalization_enabled(self):
        """Type normalization produces consistent fingerprints across similar types."""
        fingerprinter = SchemaFingerprinter(normalize_types=True)
        
        schema_int64 = {"value": "int64"}
        schema_int32 = {"value": "int32"}
        
        fp1 = fingerprinter.compute_fingerprint(schema_int64)
        fp2 = fingerprinter.compute_fingerprint(schema_int32)
        
        assert fp1 == fp2, "int64 and int32 should normalize to same fingerprint"
    
    def test_type_normalization_disabled(self):
        """With normalization disabled, different types produce different fingerprints."""
        fingerprinter = SchemaFingerprinter(normalize_types=False)
        
        schema_int64 = {"value": "int64"}
        schema_int32 = {"value": "int32"}
        
        fp1 = fingerprinter.compute_fingerprint(schema_int64)
        fp2 = fingerprinter.compute_fingerprint(schema_int32)
        
        assert fp1 != fp2, "Without normalization, int64 and int32 should differ"
    
    def test_empty_schema_raises_error(self):
        """Empty schema should raise ValueError."""
        fingerprinter = SchemaFingerprinter()
        
        with pytest.raises(ValueError, match="Cannot compute fingerprint for empty schema"):
            fingerprinter.compute_fingerprint({})
    
    def test_compute_fingerprint_from_dataframe(self):
        """Fingerprint can be computed directly from DataFrame."""
        fingerprinter = SchemaFingerprinter(normalize_types=True)
        
        df = pd.DataFrame({
            "user_id": [1, 2, 3],
            "email": ["a@test.com", "b@test.com", "c@test.com"],
        })
        
        fp = fingerprinter.compute_fingerprint_from_dataframe(df)
        
        assert isinstance(fp, str)
        assert len(fp) == 64
    
    def test_schemas_match(self):
        """schemas_match correctly identifies matching fingerprints."""
        fingerprinter = SchemaFingerprinter()
        
        fp1 = "abc123"
        fp2 = "abc123"
        fp3 = "def456"
        
        assert fingerprinter.schemas_match(fp1, fp2) is True
        assert fingerprinter.schemas_match(fp1, fp3) is False
    
    def test_get_schema_diff_no_changes(self):
        """Schema diff with identical schemas shows no changes."""
        fingerprinter = SchemaFingerprinter()
        
        schema1 = {"id": "int64", "name": "string"}
        schema2 = {"id": "int64", "name": "string"}
        
        diff = fingerprinter.get_schema_diff(schema1, schema2)
        
        assert diff["added_columns"] == []
        assert diff["removed_columns"] == []
        assert diff["changed_types"] == {}
        assert diff["is_compatible"] is True
    
    def test_get_schema_diff_added_columns(self):
        """Schema diff detects added columns."""
        fingerprinter = SchemaFingerprinter()
        
        schema1 = {"id": "int64"}
        schema2 = {"id": "int64", "name": "string"}
        
        diff = fingerprinter.get_schema_diff(schema1, schema2)
        
        assert "name" in diff["added_columns"]
        assert diff["removed_columns"] == []
        assert diff["is_compatible"] is True
    
    def test_get_schema_diff_removed_columns(self):
        """Schema diff detects removed columns."""
        fingerprinter = SchemaFingerprinter()
        
        schema1 = {"id": "int64", "name": "string"}
        schema2 = {"id": "int64"}
        
        diff = fingerprinter.get_schema_diff(schema1, schema2)
        
        assert diff["added_columns"] == []
        assert "name" in diff["removed_columns"]
        assert diff["is_compatible"] is False
    
    def test_get_schema_diff_changed_types(self):
        """Schema diff detects type changes."""
        fingerprinter = SchemaFingerprinter()
        
        schema1 = {"value": "int64"}
        schema2 = {"value": "string"}
        
        diff = fingerprinter.get_schema_diff(schema1, schema2)
        
        assert "value" in diff["changed_types"]
        assert diff["changed_types"]["value"]["from"] == "integer"
        assert diff["changed_types"]["value"]["to"] == "string"
        assert diff["is_compatible"] is False
    
    def test_normalize_type(self):
        """Type normalization mapping works correctly."""
        fingerprinter = SchemaFingerprinter(normalize_types=True)
        
        assert fingerprinter._normalize_type("int64") == "integer"
        assert fingerprinter._normalize_type("float32") == "float"
        assert fingerprinter._normalize_type("object") == "string"
        assert fingerprinter._normalize_type("datetime64[ns]") == "timestamp"
        assert fingerprinter._normalize_type("bool") == "boolean"
    
    def test_sql_type_to_string(self):
        """SQL type code conversion works correctly."""
        fingerprinter = SchemaFingerprinter()
        
        assert fingerprinter._sql_type_to_string(1) == "integer"
        assert fingerprinter._sql_type_to_string(4) == "float"
        assert fingerprinter._sql_type_to_string(8) == "string"
        assert fingerprinter._sql_type_to_string(7) == "timestamp"
        assert fingerprinter._sql_type_to_string(None) == "unknown"
        assert fingerprinter._sql_type_to_string(999) == "type_999"
    
    def test_compute_fingerprint_from_sql_result(self):
        """Fingerprint can be computed from SQL cursor description."""
        fingerprinter = SchemaFingerprinter()
        
        cursor_description = [
            ("user_id", 1, None, None, None, None, None),
            ("email", 8, None, None, None, None, None),
            ("created_at", 7, None, None, None, None, None),
        ]
        
        fp = fingerprinter.compute_fingerprint_from_sql_result(cursor_description)
        
        assert isinstance(fp, str)
        assert len(fp) == 64
    
    def test_type_normalization_constants(self):
        """Type normalization constants are defined correctly."""
        assert "int64" in TYPE_NORMALIZATION
        assert TYPE_NORMALIZATION["int64"] == "integer"
        assert TYPE_NORMALIZATION["float32"] == "float"
        assert TYPE_NORMALIZATION["object"] == "string"
    
    def test_fingerprint_deterministic_with_normalization(self):
        """Fingerprints are deterministic with type normalization."""
        fingerprinter = SchemaFingerprinter(normalize_types=True)
        
        df1 = pd.DataFrame({"value": [1, 2, 3]})
        df2 = pd.DataFrame({"value": pd.array([1, 2, 3], dtype="int32")})
        
        fp1 = fingerprinter.compute_fingerprint_from_dataframe(df1)
        fp2 = fingerprinter.compute_fingerprint_from_dataframe(df2)
        
        assert fp1 == fp2, "Different int types should normalize to same fingerprint"
    
    def test_table_name_not_in_fingerprint(self):
        """Table name parameter doesn't affect fingerprint value."""
        fingerprinter = SchemaFingerprinter()
        
        schema = {"id": "int64", "name": "string"}
        
        fp1 = fingerprinter.compute_fingerprint(schema, table_name="users")
        fp2 = fingerprinter.compute_fingerprint(schema, table_name="customers")
        fp3 = fingerprinter.compute_fingerprint(schema)
        
        assert fp1 == fp2 == fp3, "Table name should not affect fingerprint"