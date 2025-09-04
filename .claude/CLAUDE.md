# .claude Directory Instructions

## Purpose
Claude Code configuration and automation directory.

## Allowed Operations
- ✅ Read all configuration files
- ✅ Execute hooks and commands
- ✅ Update settings.json and settings.local.json
- ⚠️ Modify hooks only with explicit user approval
- ❌ Delete core configuration files

## Directory Structure
```
.claude/
├── hooks/          # Automation hooks
├── mcp/           # MCP configuration
├── commands/      # Custom commands (preserved)
├── tests/         # Test suites
├── workflows/     # Workflow templates
└── docs/          # Documentation
```

## Primary Agents
- `cicd-engineer` - Hook automation
- `workflow-automation` - Workflow management
- `system-architect` - Configuration design

## File Conventions
- Hooks: `{phase}_{action}.sh` (e.g., `pre_run.sh`)
- Configs: `{service}.yaml` or `{service}.json`
- Tests: `test_{feature}.sh`

## Key Files
- `settings.json` - Main configuration
- `settings.local.json` - Local overrides
- `mcp/clients.yaml` - MCP client settings

## Best Practices
1. Always preserve existing commands/
2. Test hooks before enabling
3. Use settings.local.json for personal config
4. Document custom workflows