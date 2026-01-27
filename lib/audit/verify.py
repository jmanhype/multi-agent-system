"""
Audit Verification - SHA256 proof verification for JSONL trade logs.

Follows the Merkle chain pattern from lib/agents/data_agent/audit/merkle_log.py.
Verifies integrity of trade logs, risk decision logs, and circuit breaker logs.
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of a single log file verification."""
    log_file: str
    total_entries: int
    valid_entries: int
    invalid_entries: int
    is_valid: bool
    errors: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_file": self.log_file,
            "total_entries": self.total_entries,
            "valid_entries": self.valid_entries,
            "invalid_entries": self.invalid_entries,
            "is_valid": self.is_valid,
            "errors": self.errors,
        }


class TradeLogVerifier:
    """Verify SHA256 proof fields on JSONL trade log entries.

    Each trade record contains a 'proof' field that is the SHA256 hash
    of all other fields in canonical JSON form (sorted keys, compact separators).
    """

    @staticmethod
    def compute_proof(record: Dict[str, Any]) -> str:
        """Recompute SHA256 proof for a trade record."""
        d = dict(record)
        d.pop("proof", None)
        canonical = json.dumps(d, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def verify_file(self, log_path: str) -> VerificationResult:
        """Verify all entries in a trade log JSONL file.

        Args:
            log_path: Path to JSONL trade log.

        Returns:
            VerificationResult with per-entry verification.
        """
        path = Path(log_path)
        errors: List[str] = []
        total = 0
        valid = 0
        invalid = 0

        if not path.exists():
            return VerificationResult(
                log_file=log_path,
                total_entries=0,
                valid_entries=0,
                invalid_entries=0,
                is_valid=True,  # No file = nothing invalid
                errors=["File does not exist"],
            )

        with open(path) as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                total += 1

                try:
                    record = json.loads(line)
                except json.JSONDecodeError as e:
                    invalid += 1
                    errors.append(f"Line {line_num}: invalid JSON - {e}")
                    continue

                stored_proof = record.get("proof", "")
                if not stored_proof:
                    # Records without proof field are skipped (older format)
                    valid += 1
                    continue

                recomputed = self.compute_proof(record)
                if recomputed != stored_proof:
                    invalid += 1
                    errors.append(
                        f"Line {line_num}: proof mismatch "
                        f"(stored={stored_proof[:16]}..., computed={recomputed[:16]}...)"
                    )
                else:
                    valid += 1

        return VerificationResult(
            log_file=log_path,
            total_entries=total,
            valid_entries=valid,
            invalid_entries=invalid,
            is_valid=(invalid == 0),
            errors=errors,
        )


class AuditVerifier:
    """Verify integrity of all system log files.

    Checks:
    - Trade logs (logs/trades.jsonl) - SHA256 proof verification
    - Paper trade logs (logs/paper_trades.jsonl) - structure check
    - Risk decision logs (logs/risk_decisions.jsonl) - structure check
    - Circuit breaker logs (logs/circuit_breaker.jsonl) - structure check
    - Alert logs (logs/alerts.jsonl) - structure check
    - Data agent audit logs (logs/data_agent_runs.jsonl) - Merkle chain
    """

    DEFAULT_LOG_FILES = {
        "trades": "logs/trades.jsonl",
        "paper_trades": "logs/paper_trades.jsonl",
        "risk_decisions": "logs/risk_decisions.jsonl",
        "circuit_breaker": "logs/circuit_breaker.jsonl",
        "alerts": "logs/alerts.jsonl",
        "runs": "logs/runs.jsonl",
    }

    def __init__(self):
        self.trade_verifier = TradeLogVerifier()

    def verify_all(self) -> Dict[str, Any]:
        """Run verification on all known log files.

        Returns:
            Dict with per-file results and overall status.
        """
        results: Dict[str, VerificationResult] = {}
        overall_valid = True

        for name, path in self.DEFAULT_LOG_FILES.items():
            if name == "trades":
                # Full SHA256 proof verification
                result = self.trade_verifier.verify_file(path)
            else:
                # Structure-only verification
                result = self._verify_jsonl_structure(path)

            results[name] = result
            if not result.is_valid:
                overall_valid = False

        # Also check Merkle chain for data agent logs
        merkle_result = self._verify_merkle_chain("logs/data_agent_runs.jsonl")
        results["data_agent_audit"] = merkle_result
        if not merkle_result.is_valid:
            overall_valid = False

        return {
            "timestamp": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
            "overall_valid": overall_valid,
            "files_checked": len(results),
            "results": {name: r.to_dict() for name, r in results.items()},
        }

    def _verify_jsonl_structure(self, log_path: str) -> VerificationResult:
        """Verify that a JSONL file has valid JSON on each line."""
        path = Path(log_path)
        errors: List[str] = []
        total = 0
        invalid = 0

        if not path.exists():
            return VerificationResult(
                log_file=log_path,
                total_entries=0,
                valid_entries=0,
                invalid_entries=0,
                is_valid=True,
                errors=[],
            )

        with open(path) as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                total += 1
                try:
                    json.loads(line)
                except json.JSONDecodeError as e:
                    invalid += 1
                    errors.append(f"Line {line_num}: invalid JSON - {e}")

        return VerificationResult(
            log_file=log_path,
            total_entries=total,
            valid_entries=total - invalid,
            invalid_entries=invalid,
            is_valid=(invalid == 0),
            errors=errors,
        )

    def _verify_merkle_chain(self, log_path: str) -> VerificationResult:
        """Verify Merkle chain integrity using data_agent audit module."""
        path = Path(log_path)
        if not path.exists():
            return VerificationResult(
                log_file=log_path,
                total_entries=0,
                valid_entries=0,
                invalid_entries=0,
                is_valid=True,
                errors=[],
            )

        try:
            from lib.agents.data_agent.audit.merkle_log import MerkleLog
            merkle = MerkleLog(log_path)
            is_valid, error_msg = merkle.verify_chain()
            stats = merkle.get_stats()

            errors = [error_msg] if error_msg else []
            return VerificationResult(
                log_file=log_path,
                total_entries=stats.get("total_entries", 0),
                valid_entries=stats.get("total_entries", 0) if is_valid else 0,
                invalid_entries=0 if is_valid else stats.get("total_entries", 0),
                is_valid=is_valid,
                errors=errors,
            )
        except ImportError:
            # Fallback to structure-only check if merkle_log not importable
            return self._verify_jsonl_structure(log_path)
