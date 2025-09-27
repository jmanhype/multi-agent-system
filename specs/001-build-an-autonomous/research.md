# Phase 0 Research: Technology Decisions

**Feature**: 001-build-an-autonomous  
**Date**: 2025-09-27  
**Status**: Complete

---

## 1. LLM Selection for Planner/Actor

**Decision**: Use Anthropic Claude or OpenAI GPT-4 via SDK, configurable via environment variable

**Rationale**:
- Claude Opus 4.1/Sonnet 4.1: Excellent at structured reasoning, tool use, and following complex instructions (ideal for Planner)
- GPT-4: Strong at code generation and data analysis patterns (suitable for Actor grounding)
- Both support function calling/tool use natively
- Constitutional requirement: LLMs offline only (research lane) - satisfied since DataAgent is research tool

**Alternatives Considered**:
- Open-source models (Llama 3, Mixtral): Lower cost but less reliable at complex planning
- Perplexity: Good for web search but not optimized for structured task decomposition
- Local models: Insufficient context window for full audit trails and schema awareness

**Implementation**:
```python
# lib/agents/data_agent/planner/intent_parser.py
llm_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
# Fallback to OpenAI if ANTHROPIC_API_KEY not set
```

---

## 2. Sandbox Technology

**Decision**: Docker containers with resource limits (primary), gVisor for high-security deployments (optional)

**Rationale**:
- Docker: Ubiquitous, well-documented, easy to enforce CPU/memory quotas via `--cpus` and `--memory`
- gVisor: Provides stronger kernel isolation for untrusted workloads, but adds complexity
- Process isolation (subprocess with resource limits): Too weak for adversarial scenarios
- Constitutional requirement VII satisfied: Tool-based execution in isolated environment

**Alternatives Considered**:
- Kubernetes pods: Overkill for single-agent use case, adds orchestration complexity
- WebAssembly (WASM): Limited library support for pandas/matplotlib
- Virtual machines: Too slow (seconds to start), excessive overhead

**Implementation**:
```python
# lib/agents/data_agent/safety/sandbox.py
import docker
client = docker.from_env()
container = client.containers.run(
    "python:3.11-slim",
    command=["python", "-c", tool_code],
    mem_limit="512m",
    cpu_quota=100000,  # 1 CPU core
    network_disabled=True,
    remove=True
)
```

**Security Notes**:
- Network disabled by default (no data exfiltration)
- Read-only filesystem except `/tmp` working directory
- Timeout enforced at 180s max per FR-023

---

## 3. Merkle Chain Implementation for Audit Logs

**Decision**: SHA256-based Merkle chain with parent hash embedded in each log entry

**Rationale**:
- SHA256: Industry standard, collision-resistant, FIPS 140-2 compliant
- Parent hash linking: Simple append-only structure, tamper-evident
- JSONL format: Human-readable, streamable, easy to parse
- Constitutional requirement III satisfied: Append-only evidence with cryptographic verification

**Alternatives Considered**:
- Blockchain (Ethereum, Hyperledger): Massive overkill, adds external dependencies
- Git-based logs: Requires repo for every analysis, complex garbage collection
- Simple append without hashing: No tamper detection

**Implementation**:
```python
# lib/agents/data_agent/audit/merkle_log.py
def append_log_entry(log_path, entry):
    with open(log_path, "r") as f:
        lines = f.readlines()
        last_hash = json.loads(lines[-1])["hash"] if lines else "0" * 64
    
    entry["timestamp"] = datetime.utcnow().isoformat()
    entry["parent_hash"] = last_hash
    entry["hash"] = hashlib.sha256(json.dumps(entry, sort_keys=True).encode()).hexdigest()
    
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
```

**Verification**:
```python
def verify_chain(log_path):
    with open(log_path, "r") as f:
        prev_hash = "0" * 64
        for line in f:
            entry = json.loads(line)
            if entry["parent_hash"] != prev_hash:
                return False  # Chain broken
            computed = hashlib.sha256(json.dumps({k: v for k, v in entry.items() if k != "hash"}, sort_keys=True).encode()).hexdigest()
            if computed != entry["hash"]:
                return False  # Entry tampered
            prev_hash = entry["hash"]
    return True
```

---

## 4. Recipe Memory Schema and Retrieval

**Decision**: SQLite database with schema fingerprints (SHA256 of sorted column names + types) as primary key

**Rationale**:
- SQLite: Serverless, zero-config, ACID guarantees, perfect for local recipe storage
- Schema fingerprint: Stable hash of table structure enables fast retrieval for similar analyses
- Intent pattern matching: Use embeddings (sentence-transformers) for semantic similarity
- Constitutional requirement VI satisfied: Format-first contracts via Pydantic models

**Alternatives Considered**:
- JSON files: No indexing, slow retrieval for 1k+ recipes
- PostgreSQL: Requires server, overkill for single-node deployment
- Redis: In-memory only, data loss on restart

**Schema**:
```sql
CREATE TABLE recipes (
    id TEXT PRIMARY KEY,                    -- UUID
    schema_fingerprint TEXT NOT NULL,       -- SHA256(sorted columns + types)
    intent_pattern TEXT NOT NULL,           -- Original user intent
    intent_embedding BLOB,                  -- sentence-transformers vector
    plan_json TEXT NOT NULL,                -- Serialized Plan object
    tool_calls TEXT NOT NULL,               -- JSON array of ToolCall objects
    success_count INTEGER DEFAULT 1,        -- Number of successful reuses
    created_at TEXT NOT NULL,
    last_used_at TEXT NOT NULL
);

CREATE INDEX idx_schema ON recipes(schema_fingerprint);
CREATE INDEX idx_created ON recipes(created_at);
```

**Retrieval Strategy**:
1. Compute schema fingerprint for current data sources
2. Query recipes with matching fingerprint
3. Rank by cosine similarity of intent embeddings
4. Return top-3 recipes for adaptation

**Implementation**:
```python
# lib/agents/data_agent/memory/recipe_store.py
def store_recipe(db_path, schema_fp, intent, plan, tool_calls):
    intent_emb = model.encode(intent)  # sentence-transformers
    recipe_id = str(uuid.uuid4())
    conn = sqlite3.connect(db_path)
    conn.execute("""
        INSERT INTO recipes (id, schema_fingerprint, intent_pattern, intent_embedding, plan_json, tool_calls, created_at, last_used_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (recipe_id, schema_fp, intent, intent_emb.tobytes(), json.dumps(plan), json.dumps(tool_calls), now, now))
    conn.commit()
```

---

## 5. Tool Validation Patterns

**Decision**: Pydantic models for all tool arguments with JSON schema validation before execution

**Rationale**:
- Pydantic: Native Python, auto-generates JSON schemas, excellent error messages
- Pre-execution validation: Catch errors before sandbox invocation (faster failure)
- Type safety: Prevents type mismatches that cause grounding errors
- Constitutional requirement VI satisfied: Format-first contracts

**Alternatives Considered**:
- Manual dict validation: Error-prone, no schema documentation
- JSON Schema validation only: Less Pythonic, no type hints
- TypeScript (Zod): Requires Node.js, adds language complexity

**Implementation**:
```python
# lib/agents/data_agent/tools/sql_runner.py
from pydantic import BaseModel, Field

class SqlQuery(BaseModel):
    query: str = Field(..., description="Parameterized SQL query with ? placeholders")
    params: list = Field(default_factory=list, description="Query parameters")
    timeout: int = Field(default=30, ge=1, le=180, description="Timeout in seconds")
    row_limit: int = Field(default=200_000, ge=1, le=200_000)

def run_sql(args: SqlQuery) -> pd.DataFrame:
    # args is validated before this function is called
    validate_sql_safety(args.query)  # Check for DDL/DML
    conn = get_connection()
    return pd.read_sql(args.query, conn, params=args.params)
```

**Validation Flow**:
1. Actor emits `{"tool": "sql.run", "args": {...}}`
2. Parse args into `SqlQuery` Pydantic model (raises ValidationError if invalid)
3. If validation passes, invoke tool in sandbox
4. If validation fails, increment retry counter and ask Planner to fix

---

## 6. Self-Repair Strategies

**Decision**: Error classification + targeted retry with LLM feedback (K=3 attempts)

**Rationale**:
- Per FR-030: 3 attempts total (initial + 2 retries)
- Error classification enables targeted fixes (SQL syntax vs. type mismatch vs. missing column)
- LLM feedback loop: Pass error message back to Planner for correction
- Constitutional requirement VIII satisfied: Test-driven approach with failure modes

**Error Categories**:
1. **SQL errors**: Syntax, invalid table/column, permission denied
2. **Type mismatches**: Casting errors, incompatible operations
3. **Missing data**: Column not found, empty result set
4. **Resource limits**: Timeout, row limit exceeded

**Retry Strategy**:
```python
# lib/agents/data_agent/actor/executor.py
def execute_with_retry(tool_call, max_attempts=3):
    for attempt in range(1, max_attempts + 1):
        try:
            result = invoke_tool(tool_call)
            return result  # Success
        except ToolError as e:
            if attempt == max_attempts:
                return FailedObservation(error=str(e), attempts=attempt)
            
            # Classify error and ask Planner to fix
            error_category = classify_error(e)
            corrected_call = planner.repair_tool_call(tool_call, error_category, str(e))
            tool_call = corrected_call
```

**Alternatives Considered**:
- Fixed retries without feedback: Wastes attempts on same error
- Exponential backoff: Irrelevant for deterministic errors (not transient)
- Human-in-the-loop: Breaks autonomy requirement

---

## Summary

All technology decisions documented and aligned with constitutional principles:

| Decision | Principle Alignment | Status |
|----------|---------------------|--------|
| Claude/GPT-4 for Planner/Actor | I (LLM offline only) | ✅ |
| Docker sandbox | V (Safety First), VII (Tool-based) | ✅ |
| Merkle-chained logs | III (Append-only evidence) | ✅ |
| SQLite recipe memory | VI (Format-first contracts) | ✅ |
| Pydantic validation | VI (Format-first contracts) | ✅ |
| Error classification + retry | VIII (TDD), FR-030 | ✅ |

**Ready for Phase 1**: Design & Contracts