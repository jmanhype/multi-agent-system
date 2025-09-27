
# Implementation Plan: Autonomous DataAgent for Natural Language Data Analysis

**Branch**: `001-build-an-autonomous` | **Date**: 2025-09-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/001-build-an-autonomous/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from file system structure or context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Build an autonomous DataAgent that accepts natural language data analysis intents and autonomously executes end-to-end workflows through a Planner→Actor loop. The agent decomposes requests into tool-based operations (SQL, Pandas, visualization), maintains Merkle-chained audit logs, implements self-repair (K=3 attempts), stores successful recipes in long-term memory, and enforces safety guardrails. Target: <30s completion for typical analyses. Integrates with GEPA trading system as black-box module with stable JSON contracts.

## Technical Context
**Language/Version**: Python 3.11+  
**Primary Dependencies**: Pydantic (contracts), psycopg3 (SQL), pandas (data ops), matplotlib/plotly (viz), anthropic/openai SDK (Planner/Actor LLMs)  
**Storage**: JSONL files (append-only audit logs), SQLite or PostgreSQL (recipe memory, schema fingerprints)  
**Testing**: pytest (unit/integration), contract tests (JSON schema validation)  
**Target Platform**: Linux server/container (Docker or gVisor sandbox)
**Project Type**: single (black-box DataAgent module in lib/agents/data_agent/)  
**Performance Goals**: <30s typical analysis completion, <10s before progress indicator, <3s per tool call  
**Constraints**: Tool-based execution only (no eval/exec), 200k row query limit, sandboxed operations, parameterized queries mandatory  
**Scale/Scope**: Support 10-20 concurrent analyses, handle datasets up to 200k rows, store 1k+ successful recipes

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Principle I: LLM Offline Research Only**
- ✅ PASS: LLMs used only in Planner/Actor (offline analysis phase), not in live trading
- DataAgent is research-lane tool; generates insights, not production trading signals

**Principle II: Black-Box Separation**
- ✅ PASS: DataAgent lives in `lib/agents/data_agent/` (implementation)
- Exposes stable JSON Request→Response contract
- Internal implementation (Planner/Actor loop) is private

**Principle III: Append-Only Evidence**
- ✅ PASS: All operations logged to `logs/data_agent_runs.jsonl`
- Merkle-chained audit trails per FR-034
- SHA256 hashes of artifacts per FR-036

**Principle IV: PR Gate Promotion**
- ✅ PASS: DataAgent is sub-agent, not strategy producer
- If used for strategy research, outputs land in research artifacts (not `artifacts/winner.json`)

**Principle V: Safety First**
- ✅ PASS: Multiple safety layers enforced
- Circuit breaker on resource exhaustion (NFR-003)
- Policy guardrails block DDL/DML (FR-016, FR-017), PII access (FR-020)
- Sandboxed execution (FR-004, NFR-003)

**Principle VI: Format-First Contracts**
- ✅ PASS: JSON schemas for AnalysisRequest and AnalysisResponse (FR-038, FR-039)
- Pydantic models with semantic versioning (FR-042)

**Principle VII: Tool-Based Execution**
- ✅ PASS: No eval/exec allowed (FR-025)
- All operations via predefined tools: sql.run, df.transform, plot.render (FR-026)
- Tool call validation before execution (FR-028)

**Principle VIII: Test-Driven Development**
- ✅ PASS: Contract tests mandatory before implementation (Phase 1)
- Integration tests with real databases (Phase 1)
- Quickstart validates user stories (Phase 1)

**Principle IX: Single Owner Modules**
- ✅ PASS: DataAgent is single module in `lib/agents/data_agent/`
- OWNERS file will designate primary owner
- Internal refactors allowed as long as JSON contract stable

**Initial Assessment**: ✅ ALL PRINCIPLES SATISFIED - No violations, proceed to Phase 0

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
lib/agents/data_agent/
├── __init__.py
├── contracts/
│   ├── request.py          # AnalysisRequest Pydantic model
│   └── response.py         # AnalysisResponse Pydantic model
├── planner/
│   ├── __init__.py
│   ├── intent_parser.py    # Parse natural language → structured plan
│   └── plan_builder.py     # Build ordered subtask graph
├── actor/
│   ├── __init__.py
│   ├── grounding.py        # Ground plan steps → tool calls
│   └── executor.py         # Execute tool calls, collect observations
├── tools/
│   ├── __init__.py
│   ├── sql_runner.py       # SQL query execution (parameterized)
│   ├── df_operations.py    # Pandas data transformations
│   ├── plotter.py          # Matplotlib/Plotly chart generation
│   └── profiler.py         # Data quality profiling
├── memory/
│   ├── __init__.py
│   ├── recipe_store.py     # SQLite/Postgres recipe storage
│   └── schema_fingerprint.py  # Schema hashing for recipe retrieval
├── safety/
│   ├── __init__.py
│   ├── policy.py           # Guardrails (PII, DDL/DML blocking)
│   └── sandbox.py          # Execution sandbox wrapper
├── audit/
│   ├── __init__.py
│   └── merkle_log.py       # Merkle-chained audit trail
└── agent.py                # Main DataAgent orchestrator

tests/
├── contract/
│   ├── test_request_schema.py
│   └── test_response_schema.py
├── integration/
│   ├── test_sql_analysis.py
│   ├── test_csv_analysis.py
│   └── test_self_repair.py
└── unit/
    ├── test_planner.py
    ├── test_actor.py
    └── test_safety.py

logs/
└── data_agent_runs.jsonl   # Append-only audit logs

db/
└── recipe_memory.db        # SQLite recipe storage
```

**Structure Decision**: Single project structure. DataAgent implemented as black-box module in `lib/agents/data_agent/` with clear separation: contracts (public API), planner/actor (core logic), tools (execution), memory (recipe storage), safety (guardrails), audit (logging). Tests organized by type (contract/integration/unit).

## Phase 0: Outline & Research
**Status**: All technical context resolved. Creating research.md with decisions.

**Research Topics**:
1. LLM selection for Planner/Actor (anthropic/openai SDK)
2. Sandbox technology (Docker, gVisor, or process isolation)
3. Merkle chain implementation for audit logs
4. Recipe memory schema and retrieval strategy
5. Tool validation patterns (JSON schema, Pydantic)
6. Self-repair strategies (error classification, retry logic)

**Output**: research.md documenting all technology decisions

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

**Status**: ✅ COMPLETE

**Outputs Generated**:
1. ✅ `data-model.md`: 7 entities (AnalysisRequest, Plan, ToolCall, Observation, Recipe, Artifact, AuditTrace) with fields, validation rules, state transitions, and storage schemas
2. ✅ `contracts/request.json`: JSON Schema for AnalysisRequest (input contract)
3. ✅ `contracts/response.json`: JSON Schema for AnalysisResponse (output contract)
4. ✅ `contracts/README.md`: Contract documentation with versioning, validation, and usage examples
5. ✅ `quickstart.md`: 4 integration test scenarios covering FR-001 through FR-043
6. ✅ `CLAUDE.md`: Updated with Python 3.11+, Pydantic, psycopg3, pandas, matplotlib/plotly

**Contract Tests** (ready for implementation):
- `tests/contract/test_request_schema.py`: Validate AnalysisRequest schema
- `tests/contract/test_response_schema.py`: Validate AnalysisResponse schema
- Tests will FAIL until DataAgent is implemented (TDD requirement)

**Integration Tests** (from quickstart.md):
- Test 1: Basic SQL analysis with artifacts + audit log (FR-001 to FR-006, FR-043)
- Test 2: Self-repair with K=3 attempts (FR-029, FR-030)
- Test 3: Policy guardrail blocks PII access (FR-020)
- Test 4: Recipe storage and retrieval (FR-031 to FR-033)

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `.specify/templates/tasks-template.md` as base
- Generate tasks from Phase 1 artifacts:
  * 2 contract test tasks from `contracts/` (request, response schemas)
  * 7 entity model tasks from `data-model.md` (AnalysisRequest, Plan, ToolCall, etc.)
  * 4 integration test tasks from `quickstart.md` (scenarios 1-4)
  * 12 implementation tasks:
    - Planner components (intent_parser, plan_builder)
    - Actor components (grounding, executor)
    - Tools (sql_runner, df_operations, plotter, profiler)
    - Memory (recipe_store, schema_fingerprint)
    - Safety (policy, sandbox)
    - Audit (merkle_log)
    - Main orchestrator (agent.py)

**Ordering Strategy** (TDD + Dependency):
1. Contract tests [P] → FAIL (no implementation)
2. Entity models [P] → contracts/, data structures
3. Integration test stubs [P] → quickstart scenarios
4. Tool implementations → sql_runner, df_operations, plotter
5. Safety layer → policy, sandbox (depends on tools)
6. Memory layer → recipe_store (depends on entities)
7. Planner → intent_parser, plan_builder (depends on entities, tools)
8. Actor → grounding, executor (depends on planner, tools, safety)
9. Audit → merkle_log (depends on all components)
10. Main orchestrator → agent.py (depends on planner, actor, audit)
11. Integration tests → Run quickstart.md scenarios

**Estimated Output**: 35-40 numbered tasks in tasks.md

**Parallelization** (marked [P]):
- Contract tests: Independent
- Entity models: Independent
- Tool implementations: Independent
- Integration test stubs: Independent

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

**Status**: No violations detected. All 9 constitutional principles satisfied.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command) → research.md created
- [x] Phase 1: Design complete (/plan command) → data-model.md, contracts/, quickstart.md, CLAUDE.md
- [x] Phase 2: Task planning complete (/plan command - describe approach only) → Ordering strategy documented
- [ ] Phase 3: Tasks generated (/tasks command) → tasks.md pending
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS (all 9 principles satisfied)
- [x] Post-Design Constitution Check: PASS (re-evaluated after Phase 1)
- [x] All NEEDS CLARIFICATION resolved (clarifications completed in spec.md)
- [x] Complexity deviations documented (none required)

---
*Based on Constitution v2.1.1 - See `/memory/constitution.md`*
