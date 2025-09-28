"""Contract tests for Audit system."""

import pytest
from pathlib import Path
import tempfile
import json

from lib.agents.data_agent.audit import MerkleLog, LogEntry, AuditTracer, EventType


class TestMerkleLogContracts:
    """Contract tests for MerkleLog."""
    
    def test_log_entry_structure(self):
        """LogEntry must have required fields."""
        entry = LogEntry(
            entry_id="test-1",
            timestamp="2025-09-27T00:00:00Z",
            event_type="test_event",
            data={"key": "value"},
            parent_hash="0" * 64,
        )
        
        assert hasattr(entry, "entry_id")
        assert hasattr(entry, "timestamp")
        assert hasattr(entry, "event_type")
        assert hasattr(entry, "data")
        assert hasattr(entry, "parent_hash")
        assert hasattr(entry, "entry_hash")
    
    def test_compute_hash_deterministic(self):
        """compute_hash() must produce same hash for same input."""
        entry1 = LogEntry(
            entry_id="test-1",
            timestamp="2025-09-27T00:00:00Z",
            event_type="test",
            data={"a": 1, "b": 2},
            parent_hash="parent123",
        )
        
        entry2 = LogEntry(
            entry_id="test-1",
            timestamp="2025-09-27T00:00:00Z",
            event_type="test",
            data={"b": 2, "a": 1},
            parent_hash="parent123",
        )
        
        hash1 = entry1.compute_hash()
        hash2 = entry2.compute_hash()
        
        assert hash1 == hash2
        assert len(hash1) == 64
    
    def test_merkle_log_initialization(self):
        """MerkleLog must initialize with empty or existing log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test.jsonl"
            log = MerkleLog(str(log_path))
            
            assert log.log_path == log_path
            assert log_path.parent.exists()
    
    def test_append_returns_log_entry(self):
        """append() must return LogEntry with computed hash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log = MerkleLog(str(Path(tmpdir) / "test.jsonl"))
            
            entry = log.append(
                entry_id="test-1",
                event_type="test",
                data={"key": "value"},
            )
            
            assert isinstance(entry, LogEntry)
            assert entry.entry_hash is not None
            assert len(entry.entry_hash) == 64
    
    def test_genesis_entry_parent_hash(self):
        """First entry must have genesis parent hash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log = MerkleLog(str(Path(tmpdir) / "test.jsonl"))
            
            entry = log.append("test-1", "test", {})
            
            assert entry.parent_hash == MerkleLog.GENESIS_HASH
    
    def test_chain_links_entries(self):
        """Second entry must link to first via parent_hash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log = MerkleLog(str(Path(tmpdir) / "test.jsonl"))
            
            entry1 = log.append("test-1", "test", {})
            entry2 = log.append("test-2", "test", {})
            
            assert entry2.parent_hash == entry1.entry_hash
    
    def test_verify_chain_valid(self):
        """verify_chain() must return (True, None) for valid chain."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log = MerkleLog(str(Path(tmpdir) / "test.jsonl"))
            
            log.append("test-1", "test", {})
            log.append("test-2", "test", {})
            
            is_valid, error = log.verify_chain()
            
            assert is_valid is True
            assert error is None
    
    def test_get_entries_filters(self):
        """get_entries() must support event_type and entry_id_prefix filters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log = MerkleLog(str(Path(tmpdir) / "test.jsonl"))
            
            log.append("req-1-event", "type_a", {})
            log.append("req-1-other", "type_b", {})
            log.append("req-2-event", "type_a", {})
            
            by_type = log.get_entries(event_type="type_a")
            assert len(by_type) == 2
            
            by_prefix = log.get_entries(entry_id_prefix="req-1")
            assert len(by_prefix) == 2
    
    def test_get_stats_structure(self):
        """get_stats() must return dict with expected keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log = MerkleLog(str(Path(tmpdir) / "test.jsonl"))
            
            log.append("test-1", "type_a", {})
            log.append("test-2", "type_b", {})
            
            stats = log.get_stats()
            
            assert "total_entries" in stats
            assert "by_event_type" in stats
            assert "chain_valid" in stats
            assert stats["total_entries"] == 2


class TestAuditTracerContracts:
    """Contract tests for AuditTracer."""
    
    def test_audit_tracer_initialization(self):
        """AuditTracer must initialize with MerkleLog."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracer = AuditTracer(str(Path(tmpdir) / "test.jsonl"))
            
            assert isinstance(tracer.log, MerkleLog)
    
    def test_event_type_enum(self):
        """EventType must define all required event types."""
        required_types = {
            "REQUEST_SUBMITTED",
            "PLAN_CREATED",
            "TOOL_CALLED",
            "OBSERVATION_RECORDED",
            "ARTIFACT_GENERATED",
            "POLICY_DECISION",
            "ERROR_OCCURRED",
        }
        
        defined_types = {e.name for e in EventType}
        
        assert required_types.issubset(defined_types)
    
    def test_log_request_signature(self):
        """log_request() must accept request_id, intent, data_sources."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracer = AuditTracer(str(Path(tmpdir) / "test.jsonl"))
            
            tracer.log_request(
                request_id="req-1",
                intent="Test query",
                data_sources=["db1", "csv1"],
            )
            
            entries = tracer.log.get_entries(event_type=EventType.REQUEST_SUBMITTED.value)
            assert len(entries) == 1
            assert entries[0].data["request_id"] == "req-1"
    
    def test_log_tool_call_signature(self):
        """log_tool_call() must accept call_id, tool_name, arguments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracer = AuditTracer(str(Path(tmpdir) / "test.jsonl"))
            
            tracer.log_tool_call(
                call_id="call-1",
                tool_name="sql_runner",
                arguments={"query": "SELECT * FROM table"},
            )
            
            entries = tracer.log.get_entries(event_type=EventType.TOOL_CALLED.value)
            assert len(entries) == 1
            assert entries[0].data["tool_name"] == "sql_runner"
    
    def test_log_observation_signature(self):
        """log_observation() must accept observation_id, call_id, status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracer = AuditTracer(str(Path(tmpdir) / "test.jsonl"))
            
            tracer.log_observation(
                observation_id="obs-1",
                call_id="call-1",
                status="success",
                execution_time_seconds=1.5,
            )
            
            entries = tracer.log.get_entries(event_type=EventType.OBSERVATION_RECORDED.value)
            assert len(entries) == 1
            assert entries[0].data["status"] == "success"
    
    def test_verify_integrity_delegates(self):
        """verify_integrity() must delegate to MerkleLog.verify_chain()."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracer = AuditTracer(str(Path(tmpdir) / "test.jsonl"))
            
            tracer.log_request("req-1", "Test", [])
            
            is_valid, error = tracer.verify_integrity()
            
            assert is_valid is True
            assert error is None
    
    def test_get_request_trace(self):
        """get_request_trace() must return all events for request."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracer = AuditTracer(str(Path(tmpdir) / "test.jsonl"))
            
            tracer.log_request("req-1", "Test", [])
            tracer.log_plan("req-1", "plan-1", 3, 10.0)
            tracer.log_request("req-2", "Other", [])
            
            trace = tracer.get_request_trace("req-1")
            
            assert len(trace) == 2
            for entry in trace:
                assert entry.entry_id.startswith("req-1")