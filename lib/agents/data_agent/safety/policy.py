"""Policy guardrails for SQL query validation and PII detection.

Implements FR-016 to FR-021: DDL/DML blocking, PII detection, column access control.
"""

import re
from dataclasses import dataclass
from typing import List, Set, Optional, Dict, Any


@dataclass
class PolicyResult:
    """Result from policy validation."""
    allowed: bool
    violations: List[str]
    severity: str
    metadata: Dict[str, Any]


@dataclass
class PIIMatch:
    """Detected PII in data."""
    pii_type: str
    value: str
    location: str
    confidence: float


class SQLPolicyChecker:
    """Check SQL queries for dangerous operations.
    
    Blocks DDL/DML statements (FR-016).
    """
    
    DDL_KEYWORDS = {
        "CREATE", "DROP", "ALTER", "TRUNCATE", "RENAME",
    }
    
    DML_KEYWORDS = {
        "INSERT", "UPDATE", "DELETE", "MERGE",
    }
    
    DANGEROUS_KEYWORDS = {
        "GRANT", "REVOKE", "EXEC", "EXECUTE", "CALL",
        "LOAD", "COPY", "IMPORT", "EXPORT",
    }
    
    def check_query(self, query: str) -> PolicyResult:
        """Check SQL query for policy violations.
        
        Args:
            query: SQL query string
        
        Returns:
            PolicyResult with violations
        """
        query_upper = query.upper()
        violations = []
        severity = "none"
        
        for keyword in self.DDL_KEYWORDS:
            if re.search(rf'\b{keyword}\b', query_upper):
                violations.append(f"DDL operation blocked: {keyword}")
                severity = "critical"
        
        for keyword in self.DML_KEYWORDS:
            if re.search(rf'\b{keyword}\b', query_upper):
                violations.append(f"DML operation blocked: {keyword}")
                severity = "critical"
        
        for keyword in self.DANGEROUS_KEYWORDS:
            if re.search(rf'\b{keyword}\b', query_upper):
                violations.append(f"Dangerous operation blocked: {keyword}")
                severity = "critical"
        
        if '--' in query and not query.strip().startswith('--'):
            violations.append("SQL comment detected (potential injection)")
            severity = max(severity, "high", key=lambda x: ["none", "low", "medium", "high", "critical"].index(x))
        
        if ';' in query.strip().rstrip(';'):
            violations.append("Multiple statements detected (potential injection)")
            severity = max(severity, "high", key=lambda x: ["none", "low", "medium", "high", "critical"].index(x))
        
        allowed = len(violations) == 0
        
        return PolicyResult(
            allowed=allowed,
            violations=violations,
            severity=severity,
            metadata={"query_length": len(query)},
        )


class PIIDetector:
    """Detect personally identifiable information in data.
    
    Implements FR-018: PII detection.
    """
    
    SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
    
    CREDIT_CARD_PATTERN = re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b')
    
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    
    PHONE_PATTERN = re.compile(r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b')
    
    def detect_pii(self, text: str, location: str = "unknown") -> List[PIIMatch]:
        """Detect PII in text.
        
        Args:
            text: Text to scan
            location: Location descriptor (e.g., "column:email", "row:42")
        
        Returns:
            List of detected PII matches
        """
        matches = []
        
        for match in self.SSN_PATTERN.finditer(str(text)):
            matches.append(PIIMatch(
                pii_type="ssn",
                value=match.group(),
                location=location,
                confidence=0.95,
            ))
        
        for match in self.CREDIT_CARD_PATTERN.finditer(str(text)):
            if self._luhn_check(match.group().replace('-', '').replace(' ', '')):
                matches.append(PIIMatch(
                    pii_type="credit_card",
                    value=match.group(),
                    location=location,
                    confidence=0.90,
                ))
        
        for match in self.EMAIL_PATTERN.finditer(str(text)):
            matches.append(PIIMatch(
                pii_type="email",
                value=match.group(),
                location=location,
                confidence=0.85,
            ))
        
        for match in self.PHONE_PATTERN.finditer(str(text)):
            matches.append(PIIMatch(
                pii_type="phone",
                value=match.group(),
                location=location,
                confidence=0.80,
            ))
        
        return matches
    
    def _luhn_check(self, card_number: str) -> bool:
        """Validate credit card using Luhn algorithm."""
        try:
            digits = [int(d) for d in card_number if d.isdigit()]
            
            if len(digits) < 13 or len(digits) > 19:
                return False
            
            checksum = 0
            for i, digit in enumerate(reversed(digits)):
                if i % 2 == 1:
                    digit *= 2
                    if digit > 9:
                        digit -= 9
                checksum += digit
            
            return checksum % 10 == 0
        
        except Exception:
            return False


class ColumnAccessControl:
    """Control access to specific columns.
    
    Implements FR-019: Column-level access control.
    """
    
    def __init__(
        self,
        allowed_patterns: Optional[List[str]] = None,
        blocked_patterns: Optional[List[str]] = None,
    ):
        """Initialize column access control.
        
        Args:
            allowed_patterns: Whitelist patterns (e.g., ["users.*", "orders.id"])
                            If None, all columns allowed by default
            blocked_patterns: Blacklist patterns (e.g., ["*.password", "*.ssn"])
        """
        self.allowed_patterns = allowed_patterns or []
        self.blocked_patterns = blocked_patterns or []
    
    def check_column_access(self, table: str, column: str) -> PolicyResult:
        """Check if column access is allowed.
        
        Args:
            table: Table name
            column: Column name
        
        Returns:
            PolicyResult indicating if access is allowed
        """
        full_name = f"{table}.{column}"
        violations = []
        
        for pattern in self.blocked_patterns:
            if self._matches_pattern(full_name, pattern):
                violations.append(f"Column access denied: {full_name} (blocked by pattern: {pattern})")
                return PolicyResult(
                    allowed=False,
                    violations=violations,
                    severity="high",
                    metadata={"table": table, "column": column},
                )
        
        if self.allowed_patterns:
            allowed = any(self._matches_pattern(full_name, pattern) for pattern in self.allowed_patterns)
            
            if not allowed:
                violations.append(f"Column access denied: {full_name} (not in whitelist)")
                return PolicyResult(
                    allowed=False,
                    violations=violations,
                    severity="medium",
                    metadata={"table": table, "column": column},
                )
        
        return PolicyResult(
            allowed=True,
            violations=[],
            severity="none",
            metadata={"table": table, "column": column},
        )
    
    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Check if name matches wildcard pattern.
        
        Args:
            name: Full column name (table.column)
            pattern: Pattern with wildcards (e.g., "users.*", "*.password")
        
        Returns:
            True if matches
        """
        pattern_regex = pattern.replace('.', r'\.').replace('*', '.*')
        pattern_regex = f'^{pattern_regex}$'
        
        return bool(re.match(pattern_regex, name))


class PolicyEnforcer:
    """Main policy enforcement coordinator.
    
    Implements FR-017, FR-020, FR-021: Query validation, violation reporting, configurable policies.
    """
    
    def __init__(
        self,
        sql_checker: Optional[SQLPolicyChecker] = None,
        pii_detector: Optional[PIIDetector] = None,
        column_access: Optional[ColumnAccessControl] = None,
    ):
        """Initialize policy enforcer.
        
        Args:
            sql_checker: SQL policy checker (uses default if None)
            pii_detector: PII detector (uses default if None)
            column_access: Column access control (uses default if None)
        """
        self.sql_checker = sql_checker or SQLPolicyChecker()
        self.pii_detector = pii_detector or PIIDetector()
        self.column_access = column_access or ColumnAccessControl(
            blocked_patterns=["*.password", "*.ssn", "*.credit_card"],
        )
    
    def validate_query(self, query: str) -> PolicyResult:
        """Validate SQL query against all policies.
        
        Args:
            query: SQL query string
        
        Returns:
            PolicyResult with combined violations
        """
        result = self.sql_checker.check_query(query)
        
        return result
    
    def scan_data_for_pii(
        self,
        data: List[Dict[str, Any]],
        table_name: str = "unknown",
    ) -> List[PIIMatch]:
        """Scan data rows for PII.
        
        Args:
            data: List of data rows (dicts)
            table_name: Table name for location tracking
        
        Returns:
            List of detected PII matches
        """
        all_matches = []
        
        for row_idx, row in enumerate(data):
            for col_name, value in row.items():
                location = f"{table_name}.{col_name}[row={row_idx}]"
                matches = self.pii_detector.detect_pii(str(value), location)
                all_matches.extend(matches)
        
        return all_matches
    
    def validate_column_access(
        self,
        table: str,
        columns: List[str],
    ) -> PolicyResult:
        """Validate access to multiple columns.
        
        Args:
            table: Table name
            columns: List of column names
        
        Returns:
            Combined PolicyResult
        """
        all_violations = []
        max_severity = "none"
        
        for column in columns:
            result = self.column_access.check_column_access(table, column)
            
            if not result.allowed:
                all_violations.extend(result.violations)
                
                severity_levels = ["none", "low", "medium", "high", "critical"]
                if severity_levels.index(result.severity) > severity_levels.index(max_severity):
                    max_severity = result.severity
        
        allowed = len(all_violations) == 0
        
        return PolicyResult(
            allowed=allowed,
            violations=all_violations,
            severity=max_severity,
            metadata={"table": table, "columns": columns},
        )