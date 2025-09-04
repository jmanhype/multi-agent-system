# Claude Hooks Directory

## Purpose
Automated hooks for Claude Code operations - pre/post execution triggers.

## Allowed Operations
- ✅ Execute existing hooks
- ✅ View hook outputs and logs
- ✅ Test hooks with dry-run
- ⚠️ Modify hooks only with explicit approval
- ⚠️ Create new hooks with validation
- ❌ Disable critical verification hooks

## Hook Types
- `pre_run.sh` - Pre-execution validation (lint, tests)
- `post_run.sh` - Post-execution analysis (review generation)
- `verify_gate.sh` - Truth score verification gate

## Primary Agents
- `cicd-engineer` - Hook development and testing
- `tester` - Hook validation
- `production-validator` - Safety verification

## Execution Context
All hooks run with:
- Working directory: Project root
- Environment variables loaded
- Git context available
- Platform config accessible

## Hook Standards
- Must be executable (`chmod +x`)
- Use `set -e` for error handling
- Support dry-run mode with `--dry-run`
- Provide verbose output with `--verbose`
- Exit codes: 0=success, 1=warning, 2=error

## Testing Hooks
```bash
# Test individual hooks
./pre_run.sh --dry-run
./post_run.sh --verbose
./verify_gate.sh --test
```

## Security
- Validate all inputs
- Never expose secrets in output
- Use secure temp directories
- Clean up resources on exit