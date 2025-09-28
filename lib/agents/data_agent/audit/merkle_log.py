"""Merkle-chained audit log for tamper detection.

Implements append-only JSONL logging with SHA256 parent hash linking.
Enables cryptographic verification of log integrity.
"""

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class LogEntry:
    """Single entry in Merkle-chained audit log.
    
    Attributes:
        entry_id: Unique entry identifier
        timestamp: ISO 8601 timestamp
        event_type: Type of event (request_submitted, tool_called, etc.)
        data: Event-specific payload
        parent_hash: SHA256 hash of previous entry (genesis entry: "0"*64)
        entry_hash: SHA256 hash of this entry (computed from all fields except this one)
    """
    entry_id: str
    timestamp: str
    event_type: str
    data: Dict[str, Any]
    parent_hash: str
    entry_hash: Optional[str] = None
    
    def compute_hash(self) -> str:
        """Compute SHA256 hash of entry fields (excluding entry_hash).
        
        Hash is computed over canonical JSON of fields in sorted order.
        """
        fields = {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "data": self.data,
            "parent_hash": self.parent_hash,
        }
        canonical = json.dumps(fields, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


class MerkleLog:
    """Append-only JSONL log with Merkle chain integrity.
    
    Features:
    - Each entry links to previous via parent_hash
    - Genesis entry has parent_hash = "0"*64
    - Tamper detection via hash chain verification
    - JSONL format for streaming and easy auditing
    """
    
    GENESIS_HASH = "0" * 64
    
    def __init__(self, log_path: str = "logs/data_agent_runs.jsonl"):
        """Initialize Merkle log.
        
        Args:
            log_path: Path to JSONL log file
        """
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash: Optional[str] = None
        self._load_last_hash()
    
    def _load_last_hash(self) -> None:
        """Load hash of last entry from file.
        
        Efficiently reads only the last line using reverse file traversal.
        """
        if not self.log_path.exists():
            self._last_hash = None
            return
        
        try:
            with open(self.log_path, 'rb') as f:
                # Seek to end of file
                f.seek(0, 2)
                file_size = f.tell()
                
                if file_size == 0:
                    self._last_hash = None
                    return
                
                # Read backwards to find last complete line
                buffer_size = min(4096, file_size)
                f.seek(max(0, file_size - buffer_size))
                
                # Read buffer and find last newline
                buffer = f.read(buffer_size).decode('utf-8')
                lines = buffer.splitlines()
                
                # Get last non-empty line
                last_line = None
                for line in reversed(lines):
                    if line.strip():
                        last_line = line.strip()
                        break
                
                if last_line:
                    entry = json.loads(last_line)
                    self._last_hash = entry.get("entry_hash")
                else:
                    self._last_hash = None
        except (json.JSONDecodeError, IOError, UnicodeDecodeError):
            self._last_hash = None
    
    def append(
        self,
        entry_id: str,
        event_type: str,
        data: Dict[str, Any],
    ) -> LogEntry:
        """Append new entry to log with Merkle chain.
        
        Args:
            entry_id: Unique identifier for this entry
            event_type: Event type (request_submitted, tool_called, etc.)
            data: Event-specific payload
        
        Returns:
            LogEntry with computed hash
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        parent_hash = self._last_hash if self._last_hash else self.GENESIS_HASH
        
        entry = LogEntry(
            entry_id=entry_id,
            timestamp=timestamp,
            event_type=event_type,
            data=data,
            parent_hash=parent_hash,
        )
        
        entry.entry_hash = entry.compute_hash()
        
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(asdict(entry)) + '\n')
        
        self._last_hash = entry.entry_hash
        return entry
    
    def verify_chain(self) -> tuple[bool, Optional[str]]:
        """Verify integrity of entire Merkle chain.
        
        Returns:
            (is_valid, error_message)
            - (True, None) if chain is valid
            - (False, error_message) if tampered or corrupted
        """
        if not self.log_path.exists():
            return (True, None)
        
        expected_parent = self.GENESIS_HASH
        entry_count = 0
        
        try:
            with open(self.log_path, 'r') as f:
                for line_num, line in enumerate(f, start=1):
                    entry_dict = json.loads(line.strip())
                    
                    if entry_dict["parent_hash"] != expected_parent:
                        return (
                            False,
                            f"Chain break at entry {entry_count + 1} (line {line_num}): "
                            f"expected parent {expected_parent[:16]}..., "
                            f"got {entry_dict['parent_hash'][:16]}..."
                        )
                    
                    entry = LogEntry(**entry_dict)
                    recomputed_hash = entry.compute_hash()
                    
                    if recomputed_hash != entry.entry_hash:
                        return (
                            False,
                            f"Hash mismatch at entry {entry_count + 1} (line {line_num}): "
                            f"stored={entry.entry_hash[:16]}..., "
                            f"computed={recomputed_hash[:16]}..."
                        )
                    
                    expected_parent = entry.entry_hash
                    entry_count += 1
            
            return (True, None)
        
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            return (False, f"Corrupted log at line {line_num}: {str(e)}")
    
    def get_entries(
        self,
        event_type: Optional[str] = None,
        entry_id_prefix: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[LogEntry]:
        """Retrieve entries matching filters.
        
        Args:
            event_type: Filter by event type
            entry_id_prefix: Filter by entry_id prefix (e.g., "request-123")
            limit: Maximum number of entries to return (most recent first)
        
        Returns:
            List of matching LogEntry objects
        """
        if not self.log_path.exists():
            return []
        
        entries: List[LogEntry] = []
        
        with open(self.log_path, 'r') as f:
            for line in f:
                entry_dict = json.loads(line.strip())
                entry = LogEntry(**entry_dict)
                
                if event_type and entry.event_type != event_type:
                    continue
                
                if entry_id_prefix and not entry.entry_id.startswith(entry_id_prefix):
                    continue
                
                entries.append(entry)
        
        if limit:
            entries = entries[-limit:]
        
        return entries
    
    def get_stats(self) -> Dict[str, Any]:
        """Get log statistics.
        
        Returns:
            Dictionary with entry counts by event type, total entries, etc.
        """
        if not self.log_path.exists():
            return {
                "total_entries": 0,
                "by_event_type": {},
                "chain_valid": True,
            }
        
        stats = {
            "total_entries": 0,
            "by_event_type": {},
        }
        
        with open(self.log_path, 'r') as f:
            for line in f:
                entry_dict = json.loads(line.strip())
                stats["total_entries"] += 1
                
                event_type = entry_dict["event_type"]
                stats["by_event_type"][event_type] = stats["by_event_type"].get(event_type, 0) + 1
        
        is_valid, error = self.verify_chain()
        stats["chain_valid"] = is_valid
        if error:
            stats["chain_error"] = error
        
        return stats