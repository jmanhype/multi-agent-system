# Tasks: Autonomous DataAgent for Natural Language Data Analysis

**Input**: Design documents from `/specs/001-build-an-autonomous/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/, quickstart.md

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → Found: plan.md with Python 3.11+, Pydantic, psycopg3 stack
2. Load optional design documents:
   → data-model.md: 7 entities extracted (AnalysisRequest, Plan, ToolCall, Observation, Recipe, Artifact, AuditTrace)
   → contracts/: 2 schemas (request.json, response.json)
   → quickstart.md: 4 test scenarios
3. Generate tasks by category:
   → Setup: project init, dependencies, linting
   → Tests: 2 contract tests, 4 integration tests
   → Core: 7 entity models, 4 tools, planner, actor, memory, safety, audit
   → Integration: Orchestrator, error handling
   → Polish: unit tests, performance, docs
4. Apply task rules:
   → Contract tests [P], entity models [P], tool implementations [P]
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001-T040)
6. Generate dependency graph
7. Create parallel execution examples
8. Validate task completeness: ✅ All contracts have tests, all entities have models
9. Return: SUCCESS (40 tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
Black-box DataAgent module: `lib/agents/data_agent/` at repository root
Tests: `tests/contract/`, `tests/integration/`, `tests/unit/`
Logs: `logs/data_agent_runs.jsonl`
Database: `db/recipe_memory.db`

## Phase 3.1: Setup
- [ ] T001 Create project structure: `lib/agents/data_agent/` with subdirs (contracts/, planner/, actor/, tools/, memory/, safety/, audit/)
- [ ] T002 Initialize Python 3.11+ project with pyproject.toml: Pydantic, psycopg3, pandas, matplotlib, anthropic, pytest dependencies
- [ ] T003 [P] Configure linting (ruff) and formatting (black) tools in pyproject.toml

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Contract Tests
- [ ] T004 [P] Contract test for AnalysisRequest schema in tests/contract/test_request_schema.py (validates request.json against Pydantic model)
- [ ] T005 [P] Contract test for AnalysisResponse schema in tests/contract/test_response_schema.py (validates response.json against Pydantic model)

### Integration Tests (from quickstart.md)
- [ ] T006 [P] Integration test: Basic SQL analysis workflow in tests/integration/test_basic_analysis.py (covers FR-001 to FR-006, FR-043)
- [ ] T007 [P] Integration test: Self-repair with K=3 attempts in tests/integration/test_self_repair.py (covers FR-029, FR-030)
- [ ] T008 [P] Integration test: PII blocking guardrails in tests/integration/test_safety_guardrails.py (covers FR-020)
- [ ] T009 [P] Integration test: Recipe storage and retrieval in tests/integration/test_recipe_reuse.py (covers FR-031 to FR-033)

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### Entity Models (from data-model.md)
- [ ] T010 [P] AnalysisRequest Pydantic model in lib/agents/data_agent/contracts/request.py (fields: request_id, intent, data_sources, constraints, deliverables, policy, timestamp)
- [ ] T011 [P] AnalysisResponse Pydantic model in lib/agents/data_agent/contracts/response.py (fields: request_id, status, artifacts, summary, metrics, audit_log_ref, plan_ref)
- [ ] T012 [P] Plan entity in lib/agents/data_agent/models/plan.py (fields: plan_id, request_id, subtasks, total_estimated_seconds, reasoning)
- [ ] T013 [P] ToolCall entity in lib/agents/data_agent/models/tool_call.py (fields: call_id, task_id, tool_name, arguments, timestamp, attempt_number)
- [ ] T014 [P] Observation entity in lib/agents/data_agent/models/observation.py (fields: observation_id, call_id, status, data, error_message, error_category, execution_time_seconds)
- [ ] T015 [P] Recipe entity in lib/agents/data_agent/models/recipe.py (fields: recipe_id, schema_fingerprint, intent_template, intent_embedding, plan_structure, success_count)
- [ ] T016 [P] Artifact entity in lib/agents/data_agent/models/artifact.py (fields: artifact_id, request_id, artifact_type, content_ref, content_hash, metadata, size_bytes)

### Tool Implementations
- [ ] T017 [P] SQL runner tool in lib/agents/data_agent/tools/sql_runner.py (parameterized queries, row limit enforcement, timeout handling)
- [ ] T018 [P] DataFrame operations tool in lib/agents/data_agent/tools/df_operations.py (filter, aggregate, join, transform operations)
- [ ] T019 [P] Plotter tool in lib/agents/data_agent/tools/plotter.py (matplotlib/plotly chart generation, save to artifacts/)
- [ ] T020 [P] Data profiler tool in lib/agents/data_agent/tools/profiler.py (schema discovery, data quality metrics)

### Safety Layer (depends on tools)
- [ ] T021 Policy guardrails in lib/agents/data_agent/safety/policy.py (DDL/DML blocking, PII detection, column access control per FR-016 to FR-021)
- [ ] T022 Sandbox wrapper in lib/agents/data_agent/safety/sandbox.py (Docker/gVisor integration, resource quotas, timeout enforcement per FR-024)

### Memory Layer (depends on entities)
- [ ] T023 Schema fingerprinting in lib/agents/data_agent/memory/schema_fingerprint.py (SHA256 hash of sorted column names + types)
- [ ] T024 Recipe storage in lib/agents/data_agent/memory/recipe_store.py (SQLite/Postgres CRUD, intent embedding with sentence-transformers, retrieval by fingerprint + similarity)

### Planner Components (depends on entities, tools)
- [ ] T025 Intent parser in lib/agents/data_agent/planner/intent_parser.py (LLM call to anthropic/openai, parse natural language → structured plan)
- [ ] T026 Plan builder in lib/agents/data_agent/planner/plan_builder.py (construct ordered subtask graph, validate DAG, estimate costs per FR-007 to FR-011)

### Actor Components (depends on planner, tools, safety)
- [ ] T027 Grounding component in lib/agents/data_agent/actor/grounding.py (translate plan subtasks → validated ToolCall objects per FR-010)
- [ ] T028 Executor with retry in lib/agents/data_agent/actor/executor.py (execute tools, collect observations, self-repair loop K=3 attempts per FR-029, FR-030)

### Audit System (depends on all components)
- [ ] T029 Merkle-chained audit log in lib/agents/data_agent/audit/merkle_log.py (append-only JSONL, SHA256 parent hash linking, verification function per FR-034, FR-037)
- [ ] T030 AuditTrace entity logging in lib/agents/data_agent/audit/tracer.py (log all events: request_submitted, plan_created, tool_called, observation_recorded, artifact_generated, policy_decision)

## Phase 3.4: Integration

### Main Orchestrator (depends on planner, actor, audit)
- [ ] T031 DataAgent orchestrator in lib/agents/data_agent/agent.py (main analyze() method, coordinates planner→actor loop, writes audit log, returns AnalysisResponse)
- [ ] T032 Error handling and partial success in lib/agents/data_agent/agent.py (graceful degradation per FR-044, clear error messages)
- [ ] T033 Progress indicators in lib/agents/data_agent/agent.py (emit progress events for analyses >10s per FR-045)
- [ ] T034 Recipe reuse integration in lib/agents/data_agent/agent.py (retrieve recipes before planning, adapt to current request per FR-033)

### Database Setup
- [ ] T035 SQLite recipe schema in db/migrations/001_create_recipes.sql (CREATE TABLE recipes with indexes on schema_fingerprint, last_used_at)
- [ ] T036 Database connection utilities in lib/agents/data_agent/db/connection.py (SQLite/Postgres connection pooling, migration runner)

## Phase 3.5: Polish

### Unit Tests
- [ ] T037 [P] Unit tests for planner in tests/unit/test_planner.py (intent parsing, plan validation, cost estimation)
- [ ] T038 [P] Unit tests for safety guardrails in tests/unit/test_safety.py (PII detection, DDL/DML blocking, parameterized query validation)

### Performance & Documentation
- [ ] T039 Performance validation: Run quickstart.md scenarios, verify <30s completion for Test 1 (per FR-043)
- [ ] T040 [P] Update CLAUDE.md with DataAgent usage examples (request/response patterns, common pitfalls)

## Dependencies

### Critical Path (TDD Order)
1. **Setup** (T001-T003) → blocks everything
2. **Tests First** (T004-T009) → MUST FAIL before implementation starts
3. **Entity Models** (T010-T016) → blocks services/tools that use them
4. **Tools** (T017-T020) → blocks safety, planner, actor
5. **Safety** (T021-T022) → blocks actor execution
6. **Memory** (T023-T024) → blocks recipe reuse
7. **Planner** (T025-T026) → blocks actor grounding
8. **Actor** (T027-T028) → blocks orchestrator
9. **Audit** (T029-T030) → blocks orchestrator
10. **Orchestrator** (T031-T036) → enables integration tests to PASS
11. **Polish** (T037-T040) → final validation

### Detailed Dependencies
- T004-T009 (tests) before T010-T040 (implementation)
- T010-T016 (entities) before T021-T030 (services using entities)
- T017-T020 (tools) before T021-T022, T025-T028 (components using tools)
- T021-T022 (safety) before T028 (executor needs policy checks)
- T023-T024 (memory) before T034 (recipe reuse)
- T025-T026 (planner) before T027 (grounding needs plans)
- T027-T028 (actor) before T031 (orchestrator needs execution)
- T029-T030 (audit) before T031 (orchestrator logs events)
- T031-T034 (orchestrator) before T039 (integration tests)
- T035-T036 (database) before T024, T031 (recipe storage, orchestrator)

## Parallel Execution Examples

### Phase 3.2: Launch all tests together
```bash
# T004-T009 can run in parallel (different test files)
pytest tests/contract/test_request_schema.py &
pytest tests/contract/test_response_schema.py &
pytest tests/integration/test_basic_analysis.py &
pytest tests/integration/test_self_repair.py &
pytest tests/integration/test_safety_guardrails.py &
pytest tests/integration/test_recipe_reuse.py &
wait
```

### Phase 3.3: Launch entity models in parallel
```bash
# T010-T016 can run in parallel (different entity files)
# Example with code editor/IDE:
# - Open 7 files simultaneously
# - Implement each Pydantic model independently
```

### Phase 3.3: Launch tools in parallel
```bash
# T017-T020 can run in parallel (different tool files)
# Example:
# - Team member A implements sql_runner.py
# - Team member B implements df_operations.py
# - Team member C implements plotter.py
# - Team member D implements profiler.py
```

## Notes
- [P] tasks = different files, no dependencies
- Verify all tests FAIL before implementing (T004-T009 should fail with ImportError or NotImplementedError)
- Commit after completing each task
- Run integration tests (T006-T009) after T031 completes to verify end-to-end workflow
- Recipe reuse (T034) is optional enhancement; system works without it
- Performance target (FR-043): 80%+ of typical analyses <30s

## Validation Checklist
*GATE: Checked before marking tasks.md as complete*

- [x] All contracts have corresponding tests (T004-T005 test request.json, response.json)
- [x] All entities have model tasks (T010-T016 cover all 7 entities from data-model.md)
- [x] All tests come before implementation (T004-T009 before T010-T040)
- [x] Parallel tasks truly independent (contract tests, entity models, tool implementations in different files)
- [x] Each task specifies exact file path (all tasks include lib/agents/data_agent/* or tests/* paths)
- [x] No task modifies same file as another [P] task (verified: no file path conflicts)

---

**Status**: Tasks generated | **Total**: 40 tasks | **Parallel**: 16 tasks | **Estimated Duration**: 8-10 days (single developer)