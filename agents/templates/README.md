# Templates Agents Collection

## Overview

The Templates collection provides reusable agent patterns, scaffolding, and standardized implementations for common agent types and workflows.

## Template Categories

### Core Templates
- **Task Orchestrator** (`orchestrator-task.md`)
- **Coordinator Swarm Init** (`coordinator-swarm-init.md`)
- **GitHub PR Manager** (`github-pr-manager.md`)
- **SPARC Coordinator** (`sparc-coordinator.md`)
- **Performance Analyzer** (`performance-analyzer.md`)

### Specialized Templates
- **Memory Coordinator** (`memory-coordinator.md`)
- **Migration Plan** (`migration-plan.md`)
- **Automation Smart Agent** (`automation-smart-agent.md`)
- **Implementer SPARC Coder** (`implementer-sparc-coder.md`)

## Template Structure

```yaml
name: template-name
type: template-type
base: parent-template
parameters:
  - name: param1
    type: string
    required: true
  - name: param2
    type: number
    default: 10
hooks:
  pre: validation-hook
  post: cleanup-hook
capabilities:
  - capability1
  - capability2
```

## Usage Pattern

```javascript
// Instantiate from template
const agent = await createFromTemplate('orchestrator-task', {
  name: 'my-orchestrator',
  config: {
    maxWorkers: 5,
    timeout: 3000
  }
});
```

## Best Practices

- Use templates for consistency
- Customize only when necessary
- Document modifications
- Version template changes
- Test template instances

---

For template specifications, refer to individual template files.
