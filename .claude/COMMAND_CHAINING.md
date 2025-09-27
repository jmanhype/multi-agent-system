# Claude Code Command Chaining Architecture

**Version**: 1.0.0  
**Date**: 2025-09-27  
**Feature**: SlashCommand tool (requires Claude Code >= 1.0.124)

## Overview

Claude Code's `SlashCommand` tool enables agents to programmatically invoke custom slash commands during conversations, enabling sophisticated workflow automation and command orchestration.

## Key Discovery

**Source**: [Claude Code Slash Commands Documentation](https://docs.claude.com/en/docs/claude-code/slash-commands)

> "This gives Claude the ability to invoke custom commands on your behalf when appropriate."

### Requirements for Automated Invocation

1. **Description frontmatter**: Commands must have a `description` field
2. **User-defined only**: Built-in commands are not supported
3. **Version requirement**: Claude Code >= 1.0.124
4. **Discovery**: Run `claude --debug` to see supported commands

## Implementation Strategy

### 1. Enhanced Slash Commands

All slash commands now include proper frontmatter:

```markdown
---
description: Brief description of command purpose
allowed-tools: Bash, Read, Write, Edit
---

Command implementation with $ARGUMENTS placeholder
```

### 2. Workflow Orchestration Commands

#### `/sdd-workflow` - Complete SDD Pipeline
**Location**: `.claude/commands/sdd-workflow.md`

**Purpose**: Execute full Specification-Driven Development workflow

**Chaining Pattern**:
```
/sdd-workflow <feature description>
  ↓
  1. Run /constitution (if needed)
  2. Run /specify $ARGUMENTS
  3. Run /clarify
  4. Run /plan
  5. Run /tasks
  6. Run /implement
```

**Gate Checks**:
- Constitution must exist before specification
- Clarifications must resolve before planning
- Plan artifacts complete before task generation
- All tasks defined before implementation

#### `/analyze-data` - DataAgent Orchestration
**Location**: `.claude/commands/analyze-data.md`

**Purpose**: Autonomous data analysis with safety enforcement

**Chaining Pattern**:
```
/analyze-data <natural language query>
  ↓
  Safety Pre-Flight → Planner → Actor → Response Assembly
```

**Internal Tool Orchestration**:
- SQL query validation and execution
- Pandas data transformations
- Matplotlib/Plotly visualizations
- Audit trail generation

### 3. Safety Hooks

#### Pre-Execution Hook: SQL Validation
**Location**: `.claude/hooks/pre_data_agent_sql.sh`

**Validates**:
- No DDL operations (CREATE, DROP, ALTER, TRUNCATE)
- No DML operations (INSERT, UPDATE, DELETE, MERGE)
- No system table access (pg_*, information_schema.*)
- No SQL injection patterns

**Exit Codes**:
- `0`: Validation passed
- `1`: Policy violation (blocks execution)

#### Post-Execution Hook: Audit Logging
**Location**: `.claude/hooks/post_data_agent_execution.sh`

**Generates**:
- Append-only JSONL audit logs
- Merkle-chained entries (SHA256)
- Tamper-evident forensic trail

**Log Location**: `.taskmaster/logs/data_agent_audit.jsonl`

### 4. Subagent Definition

#### DataAgent Subagent
**Location**: `.claude/agents/data/data-agent.md`

**Frontmatter**:
```yaml
---
name: data-agent
description: Autonomous natural language data analysis with SQL, Pandas, and visualization
tools: Bash, Read, Write
model: sonnet
---
```

**Trigger Phrases**: "analyze data", "query database", "show trends", "generate report", "visualize"

**Automatic Delegation**: Claude proactively invokes when user mentions data analysis

## Command Invocation Patterns

### Manual Sequential (Traditional)
```bash
/constitution
/specify "build authentication system"
/clarify
/plan
/tasks
/implement
```

### Automated Orchestration (New)
```bash
/sdd-workflow "build authentication system"
# Claude automatically chains: constitution → specify → clarify → plan → tasks → implement
```

### Subagent Delegation
```bash
# Explicit
> Use the data-agent subagent to analyze Q1 sales trends

# Automatic (based on trigger phrases)
> Show me trends in last 30 days of BTC trading volume
# Claude auto-delegates to data-agent
```

### Data Analysis with Safety
```bash
/analyze-data "Analyze Q1 2021 Arizona sales; trends + charts"
# Triggers:
#   1. pre_data_agent_sql.sh (validates query safety)
#   2. DataAgent Planner→Actor loop
#   3. post_data_agent_execution.sh (audit logging)
```

## Architecture Benefits

### Before Command Chaining
- **Manual workflow**: User runs 6 separate commands
- **Context loss**: Each command invocation risks losing context
- **Error-prone**: Users might skip critical steps (e.g., /clarify)
- **No automation**: Repetitive typing for common workflows

### After Command Chaining
- **Single invocation**: One command orchestrates entire workflow
- **Context preservation**: Claude maintains state across chained commands
- **Gate enforcement**: Mandatory checkpoints prevent skipping critical steps
- **Reusable patterns**: Common workflows encoded as slash commands

## Best Practices

### 1. Command Design
- **Clear descriptions**: Enable accurate automatic invocation
- **Explicit tool lists**: `allowed-tools` restricts capabilities
- **Error handling**: Commands should gracefully handle failures
- **Progress reporting**: Update user at each chaining step

### 2. Hook Integration
- **Pre-hooks for validation**: Block unsafe operations before execution
- **Post-hooks for logging**: Audit all operations for forensics
- **Exit codes**: Use standard codes (0 = success, 1 = error)
- **Idempotency**: Hooks should be safe to retry

### 3. Subagent Delegation
- **Focused purpose**: Single responsibility per agent
- **Clear triggers**: Define when agent should be invoked
- **Tool restrictions**: Limit agent capabilities via `tools` frontmatter
- **Model selection**: Choose appropriate model for agent complexity

## Testing Command Chains

### Verify Command Discovery
```bash
claude --debug
# Should list all commands with descriptions
```

### Test Individual Commands
```bash
/analyze-data "test query"
# Verify safety hooks fire correctly
```

### Test Workflow Orchestration
```bash
/sdd-workflow "simple feature"
# Observe each chained command execution
```

### Validate Audit Logs
```bash
cat .taskmaster/logs/data_agent_audit.jsonl | jq .
# Verify Merkle chain integrity
```

## Migration Guide

### Updating Existing Commands

**Before** (no chaining support):
```markdown
# my-command.md
Execute some workflow...
```

**After** (chaining enabled):
```markdown
---
description: Execute some workflow
allowed-tools: Bash, Read
---

Execute some workflow...

When appropriate, run /other-command to continue.
```

### Adding Safety Hooks

1. Create hook script in `.claude/hooks/`
2. Make executable: `chmod +x hook-script.sh`
3. Reference in command or configure in settings
4. Test with edge cases and error conditions

### Defining Subagents

1. Create agent file in `.claude/agents/<category>/`
2. Add YAML frontmatter with name, description, tools, model
3. Document trigger phrases and use cases
4. Test automatic delegation with various user inputs

## Constitutional Compliance

### Principle I: LLM Offline Research Only
✅ Command chaining is deterministic orchestration (not LLM-dependent)  
✅ Safety hooks validate before LLM operations

### Principle II: Black-Box Separation
✅ Commands in `.claude/` (control plane)  
✅ Implementation in `lib/` (data plane)

### Principle III: Append-Only Evidence
✅ Audit hooks create tamper-evident logs  
✅ Merkle chains provide cryptographic integrity

### Principle V: Safety First
✅ Pre-hooks block unsafe operations  
✅ Post-hooks provide forensic audit trail

### Principle VII: Tool-Based Execution
✅ `allowed-tools` restricts command capabilities  
✅ No eval/exec in command implementations

## Resources

### Documentation
- [Claude Code Slash Commands](https://docs.claude.com/en/docs/claude-code/slash-commands)
- [Claude Code Subagents](https://docs.claude.com/en/docs/claude-code/sub-agents)
- [Claude Code Hooks](https://docs.claude.com/en/docs/claude-code/hooks-guide)

### Example Repositories
- [wshobson/commands](https://github.com/wshobson/commands) - 56 production-ready commands
- [wshobson/agents](https://github.com/wshobson/agents) - Specialized subagent collection

### Internal Files
- `.claude/commands/` - All slash command definitions
- `.claude/agents/` - Subagent definitions with frontmatter
- `.claude/hooks/` - Pre/post-execution hooks
- `.specify/memory/constitution.md` - Governance principles

---

**Status**: Architecture implemented and validated  
**Next Steps**: Resume core DataAgent implementation (T012-T040)