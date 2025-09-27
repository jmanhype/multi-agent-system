# Data Model: DataAgent Entities

**Feature**: 001-build-an-autonomous  
**Date**: 2025-09-27  
**Source**: Extracted from spec.md Key Entities (lines 179-188)

---

## Entity Definitions

### 1. AnalysisRequest

Represents a user's natural language intent with associated data sources, constraints, deliverables, and policy requirements.

**Fields**:
- `request_id` (string, UUID): Unique identifier for the analysis request
- `intent` (string): Natural language description of what to analyze (e.g., "Analyze Q1 2021 Arizona sales; trends + charts")
- `data_sources` (array of DataSource): List of data sources to query
  - `type` (enum): "sql" | "csv" | "json"
  - `connection_string` (string): For SQL databases
  - `file_path` (string): For file-based sources
  - `schema_fingerprint` (string, SHA256): Hash of schema for recipe retrieval
- `constraints` (object): User-specified limits
  - `row_limit` (int, default 200000): Max rows to return per query
  - `timeout_seconds` (int, default 30): Max time per analysis
- `deliverables` (array of enum): ["tables", "charts", "reports", "summary"]
- `policy` (object): Safety and access control
  - `allowed_columns` (array of string): Whitelist, if applicable
  - `blocked_patterns` (array of string): PII patterns to reject
- `timestamp` (string, ISO 8601): Request submission time

**Validation Rules**:
- `intent` MUST be non-empty string (max 2000 chars)
- `data_sources` MUST have at least 1 entry
- `constraints.row_limit` MUST be between 1 and 200,000 (per FR-022)
- `constraints.timeout_seconds` MUST be between 1 and 180 (per FR-023)

**State Transitions**:
```
submitted → planning → executing → [completed | failed | partial_success]
```

---

### 2. Plan

Ordered sequence of subtasks derived from an AnalysisRequest, including tool selections, invariants, and cost estimates.

**Fields**:
- `plan_id` (string, UUID): Unique identifier
- `request_id` (string, UUID): Foreign key to AnalysisRequest
- `subtasks` (array of Subtask):
  - `task_id` (string): Unique within plan (e.g., "load_sales_data")
  - `description` (string): Human-readable task description
  - `tool_name` (enum): "sql.run" | "df.transform" | "plot.render" | "profiler.analyze"
  - `dependencies` (array of string): task_ids that must complete first
  - `invariants` (array of string): Constraints to enforce (e.g., "filter before aggregate")
  - `estimated_cost_seconds` (float): Expected execution time
- `total_estimated_seconds` (float): Sum of all subtask costs
- `created_at` (string, ISO 8601): Plan generation time
- `reasoning` (string): Planner's rationale for this plan structure

**Validation Rules**:
- `subtasks` MUST form a directed acyclic graph (no circular dependencies)
- Sum of `estimated_cost_seconds` MUST be ≤ `request.constraints.timeout_seconds`
- Each subtask's `tool_name` MUST be in registered tool set

**State Transitions**:
```
draft → validated → executing → [completed | abandoned]
```

**Example**:
```json
{
  "plan_id": "550e8400-e29b-41d4-a716-446655440000",
  "subtasks": [
    {
      "task_id": "load_sales",
      "description": "Load Q1 2021 sales from database",
      "tool_name": "sql.run",
      "dependencies": [],
      "invariants": ["WHERE state='Arizona' AND date >= '2021-01-01'"],
      "estimated_cost_seconds": 2.5
    },
    {
      "task_id": "aggregate_monthly",
      "description": "Aggregate sales by month",
      "tool_name": "df.transform",
      "dependencies": ["load_sales"],
      "invariants": ["group by month before sum"],
      "estimated_cost_seconds": 0.5
    },
    {
      "task_id": "plot_trend",
      "description": "Generate trend line chart",
      "tool_name": "plot.render",
      "dependencies": ["aggregate_monthly"],
      "invariants": [],
      "estimated_cost_seconds": 1.0
    }
  ],
  "total_estimated_seconds": 4.0
}
```

---

### 3. ToolCall

Structured action emitted by Actor, specifying tool name and validated arguments.

**Fields**:
- `call_id` (string, UUID): Unique identifier for this invocation
- `task_id` (string): References subtask in Plan
- `tool_name` (enum): "sql.run" | "df.transform" | "plot.render" | "profiler.analyze"
- `arguments` (object): Tool-specific validated args (Pydantic model serialized)
  - For "sql.run": `{query: str, params: list, timeout: int, row_limit: int}`
  - For "df.transform": `{operation: str, columns: list, aggregation: str}`
  - For "plot.render": `{type: str, x_col: str, y_col: str, title: str}`
- `timestamp` (string, ISO 8601): Call invocation time
- `attempt_number` (int, 1-3): Retry attempt (1 = initial, 2-3 = retries per FR-030)

**Validation Rules**:
- `arguments` MUST validate against tool's Pydantic schema before execution (per FR-028)
- `tool_name` MUST exist in registered tool set
- `attempt_number` MUST be ≤ 3 (per FR-030: K=3 attempts)

**State Transitions**:
```
pending → executing → [succeeded | failed] → (if failed and attempts < 3) → pending (retry)
```

---

### 4. Observation

Result returned from tool execution, including success/failure status, data, and error details.

**Fields**:
- `observation_id` (string, UUID): Unique identifier
- `call_id` (string, UUID): Foreign key to ToolCall
- `status` (enum): "success" | "error" | "timeout" | "resource_limit"
- `data` (object, nullable): Tool output (serialized DataFrame, chart path, or profile stats)
- `error_message` (string, nullable): If status != "success"
- `error_category` (enum, nullable): "sql_syntax" | "type_mismatch" | "missing_column" | "resource_exhausted"
- `execution_time_seconds` (float): Actual execution duration
- `row_count` (int, nullable): For data operations
- `timestamp` (string, ISO 8601): Observation capture time

**Validation Rules**:
- If `status` = "success", `data` MUST be non-null
- If `status` != "success", `error_message` and `error_category` MUST be non-null
- `execution_time_seconds` MUST be > 0

**Error Categories** (for self-repair per FR-029):
- `sql_syntax`: Invalid SQL (missing quotes, wrong keywords)
- `type_mismatch`: Column type incompatible with operation (e.g., AVG on string)
- `missing_column`: Referenced column doesn't exist in schema
- `resource_exhausted`: Timeout or row limit exceeded

---

### 5. Recipe

Successful analysis pattern stored in long-term memory, including schema fingerprint, intent template, plan structure, and tool arguments.

**Fields**:
- `recipe_id` (string, UUID): Unique identifier
- `schema_fingerprint` (string, SHA256): Hash of data source schemas (for retrieval)
- `intent_template` (string): Generalized intent pattern (e.g., "Analyze {time_range} {location} sales; trends + charts")
- `intent_embedding` (blob): Sentence-transformer vector for semantic search
- `plan_structure` (object): Reusable plan template
  - `subtasks` (array): Same as Plan.subtasks but with parameterized arguments
- `tool_argument_templates` (array): Argument patterns for each tool call
- `success_count` (int): Number of times this recipe was successfully reused
- `created_at` (string, ISO 8601): First successful use
- `last_used_at` (string, ISO 8601): Most recent reuse

**Validation Rules**:
- `schema_fingerprint` MUST be SHA256 hash (64 hex chars)
- `success_count` MUST be ≥ 1
- `intent_template` MUST have placeholders in `{braces}` format

**Retrieval Strategy** (per FR-031, FR-033):
1. Compute schema fingerprint for incoming request
2. Query recipes with matching `schema_fingerprint`
3. Rank by cosine similarity of `intent_embedding` to request intent
4. Return top-3 recipes for adaptation

**Example**:
```json
{
  "recipe_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "schema_fingerprint": "a3f5b8c...",
  "intent_template": "Analyze {time_range} {location} sales; trends + charts",
  "plan_structure": {
    "subtasks": [
      {"task_id": "load_data", "tool_name": "sql.run", "arg_template": "SELECT * FROM sales WHERE date BETWEEN {start} AND {end} AND state={location}"},
      {"task_id": "aggregate", "tool_name": "df.transform", "arg_template": "GROUP BY month, SUM(amount)"},
      {"task_id": "plot", "tool_name": "plot.render", "arg_template": "line chart"}
    ]
  },
  "success_count": 12,
  "created_at": "2025-09-15T10:30:00Z",
  "last_used_at": "2025-09-27T08:45:00Z"
}
```

---

### 6. Artifact

Tangible output from analysis (table, chart, report) with metadata and content reference.

**Fields**:
- `artifact_id` (string, UUID): Unique identifier
- `request_id` (string, UUID): Foreign key to AnalysisRequest
- `artifact_type` (enum): "table" | "chart" | "report" | "summary"
- `content_ref` (string): File path or S3 URI to artifact content
- `content_hash` (string, SHA256): Hash of artifact for audit trail (per FR-036)
- `metadata` (object): Type-specific metadata
  - For "table": `{row_count: int, column_names: list}`
  - For "chart": `{chart_type: str, x_label: str, y_label: str}`
  - For "report": `{format: str, section_count: int}`
- `size_bytes` (int): Artifact file size
- `created_at` (string, ISO 8601): Artifact generation time

**Validation Rules**:
- `content_ref` MUST be valid file path or URI
- `content_hash` MUST be SHA256 hash (64 hex chars) matching actual file
- `artifact_type` MUST be in AnalysisRequest.deliverables

**Storage**:
- Tables: CSV files in `artifacts/tables/{request_id}/`
- Charts: PNG files in `artifacts/charts/{request_id}/`
- Reports: Markdown files in `artifacts/reports/{request_id}/`

---

### 7. AuditTrace

Immutable, Merkle-chained log of all steps, decisions, and artifacts in an analysis workflow.

**Fields**:
- `entry_id` (string, UUID): Unique identifier for this log entry
- `request_id` (string, UUID): Foreign key to AnalysisRequest
- `sequence_number` (int): Entry position in chain (starts at 1)
- `parent_hash` (string, SHA256): Hash of previous log entry (or "0"*64 for first entry)
- `timestamp` (string, ISO 8601): Entry creation time
- `event_type` (enum): "request_submitted" | "plan_created" | "tool_called" | "observation_recorded" | "artifact_generated" | "policy_decision"
- `event_data` (object): Type-specific payload
  - For "tool_called": `{call_id: str, tool_name: str, arguments: object}`
  - For "policy_decision": `{decision: str, rule: str, reason: str}`
- `actor` (string): Component that generated this event ("planner" | "actor" | "safety")
- `hash` (string, SHA256): SHA256(parent_hash + timestamp + event_type + event_data)

**Validation Rules** (per FR-034, FR-037):
- `sequence_number` MUST be monotonically increasing
- `parent_hash` MUST match previous entry's `hash`
- `hash` MUST be computed correctly (SHA256 of specified fields)
- Entries MUST be append-only (no updates or deletes)

**Verification Function**:
```python
def verify_audit_chain(log_path):
    with open(log_path, "r") as f:
        entries = [json.loads(line) for line in f]
    
    for i, entry in enumerate(entries):
        # Check sequence
        if entry["sequence_number"] != i + 1:
            return False
        
        # Check parent hash
        expected_parent = entries[i-1]["hash"] if i > 0 else "0" * 64
        if entry["parent_hash"] != expected_parent:
            return False
        
        # Check hash computation
        payload = f"{entry['parent_hash']}{entry['timestamp']}{entry['event_type']}{json.dumps(entry['event_data'], sort_keys=True)}"
        computed_hash = hashlib.sha256(payload.encode()).hexdigest()
        if computed_hash != entry["hash"]:
            return False
    
    return True
```

---

## Entity Relationships

```
AnalysisRequest (1) ──> (1) Plan ──> (N) Subtask
                │                           │
                │                           V
                │                      ToolCall (1) ──> (1) Observation
                │
                ├──> (N) Artifact
                │
                └──> (N) AuditTrace

Recipe (stored separately, retrieved by schema_fingerprint + intent_embedding)
```

**Lifecycle**:
1. User submits `AnalysisRequest`
2. Planner generates `Plan` with subtasks
3. Actor grounds each subtask into `ToolCall`
4. Tools execute, return `Observation`
5. If observation fails, retry up to K=3 times (per FR-030)
6. Successful observations produce `Artifact`
7. All events logged to `AuditTrace` (Merkle-chained)
8. On success, store `Recipe` for future reuse

---

## Storage Schema

**SQLite Database** (`db/recipe_memory.db`):
```sql
CREATE TABLE recipes (
    recipe_id TEXT PRIMARY KEY,
    schema_fingerprint TEXT NOT NULL,
    intent_template TEXT NOT NULL,
    intent_embedding BLOB NOT NULL,
    plan_structure TEXT NOT NULL,       -- JSON
    tool_argument_templates TEXT NOT NULL,  -- JSON
    success_count INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    last_used_at TEXT NOT NULL
);

CREATE INDEX idx_schema_fp ON recipes(schema_fingerprint);
CREATE INDEX idx_last_used ON recipes(last_used_at DESC);
```

**JSONL Logs** (`logs/data_agent_runs.jsonl`):
```jsonl
{"entry_id": "...", "request_id": "...", "sequence_number": 1, "parent_hash": "000...", "timestamp": "...", "event_type": "request_submitted", "event_data": {...}, "actor": "system", "hash": "abc..."}
{"entry_id": "...", "request_id": "...", "sequence_number": 2, "parent_hash": "abc...", "timestamp": "...", "event_type": "plan_created", "event_data": {...}, "actor": "planner", "hash": "def..."}
...
```

**File System** (`artifacts/`):
```
artifacts/
├── tables/
│   └── {request_id}/
│       └── result.csv
├── charts/
│   └── {request_id}/
│       └── trend.png
└── reports/
    └── {request_id}/
        └── summary.md
```

---

**Version**: 1.0.0 | **Last Updated**: 2025-09-27