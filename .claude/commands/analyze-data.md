---
description: Autonomous data analysis with SQL, Pandas, and visualization using the DataAgent
allowed-tools: Bash, Read, Write, Edit
---

Execute DataAgent analysis workflow for: $ARGUMENTS

**Safety Pre-Flight:**
1. Validate request against safety policies:
   - No DDL/DML operations (CREATE, DROP, ALTER, DELETE, UPDATE, INSERT, TRUNCATE, MERGE)
   - No system table access (pg_*, information_schema.*)
   - No PII exposure without explicit masking
   - Row limit: 10,000 per query
   - Timeout: 30 seconds per operation

2. If safety violations detected:
   - Block execution immediately
   - Report policy violation with rationale
   - Suggest compliant alternative approach

**Planner Phase:**
1. Parse natural language request into structured analysis goal
2. Decompose into concrete workflow steps:
   - SQL queries for data retrieval
   - Pandas operations for transformations
   - Visualization specs for outputs
3. Generate grounded plan with tool calls

**Actor Phase:**
1. Execute plan step-by-step:
   - Run SQL queries (read-only, parameterized)
   - Apply Pandas transformations
   - Generate plots (matplotlib/plotly)
   - Compile intermediate results

2. Self-repair on errors (K=3 attempts):
   - Detect SQL syntax errors, schema mismatches
   - Regenerate corrected query
   - Retry with exponential backoff

3. Store successful patterns in recipe memory:
   - Key: (schema_fingerprint, intent_embedding)
   - Value: (plan, tool_calls, performance_metrics)

**Response Assembly:**
1. Package artifacts:
   - DataFrame CSVs
   - Plot images (PNG/SVG)
   - Summary statistics
   - Audit trace (Merkle-chained)

2. Return AnalysisResponse JSON:
   ```json
   {
     "status": "success|error",
     "artifacts": [...],
     "audit_id": "merkle_root_hash",
     "recipe_id": "pattern_uuid"
   }
   ```

**Audit Logging:**
- Append-only JSONL to `.taskmaster/logs/data_agent_audit.jsonl`
- Include: timestamp, request, plan, tool_calls, observations, artifacts, merkle_hash
- Cryptographically link to previous log entry

**Error Handling:**
- Invalid SQL → Self-repair loop (max 3 attempts)
- Timeout → Return partial results + timeout notice
- Policy violation → Block + suggest compliant path
- Unexpected error → Fail-safe, full audit trace

**Recipe Memory Integration:**
- On success: Store (schema, intent) → (plan, metrics)
- On future similar requests: Retrieve and adapt proven patterns
- Continuous learning without manual intervention

**Output Format:**
Return structured AnalysisResponse with:
- Status and artifacts
- Execution time and resource usage
- Audit trail ID for forensic review
- Suggested follow-up analyses