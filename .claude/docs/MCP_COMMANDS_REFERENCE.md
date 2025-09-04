# 📚 MCP Commands Reference Guide

## 🚀 Claude Flow Core Commands

### Swarm Orchestration
```bash
# Initialize swarm with topology
npx claude-flow@alpha swarm init --topology [mesh|star|ring|hybrid]

# Spawn agents
npx claude-flow@alpha agent spawn --type [coder|reviewer|tester|planner|researcher]

# Task orchestration
npx claude-flow@alpha task orchestrate --description "Task description"

# Monitor swarm
npx claude-flow@alpha swarm monitor
npx claude-flow@alpha swarm status

# List agents
npx claude-flow@alpha agent list
npx claude-flow@alpha agent metrics --agent-id [id]
```

### SPARC Methodology
```bash
# List available modes
npx claude-flow@alpha sparc modes

# Run specific mode
npx claude-flow@alpha sparc run [spec|pseudocode|architect|refinement|completion] "task"

# TDD workflow
npx claude-flow@alpha sparc tdd "feature description"

# Batch processing
npx claude-flow@alpha sparc batch "spec pseudocode architect" "task"

# Pipeline execution
npx claude-flow@alpha sparc pipeline "complete task description"

# Get mode info
npx claude-flow@alpha sparc info [mode]
```

### Memory Management
```bash
# Check memory usage
npx claude-flow@alpha memory usage

# Search memory
npx claude-flow@alpha memory search --query "search term"

# Store in memory
npx claude-flow@alpha memory store --key "key" --value "value"

# Retrieve from memory
npx claude-flow@alpha memory get --key "key"
```

### Performance Analysis
```bash
# Generate performance report
npx claude-flow@alpha performance report

# Analyze bottlenecks
npx claude-flow@alpha bottleneck analyze

# Token usage
npx claude-flow@alpha token usage

# Benchmark
npx claude-flow@alpha benchmark run --iterations 10
```

### Hooks System
```bash
# Pre-command hook
npx claude-flow@alpha hooks pre-command --command "command"

# Post-command hook
npx claude-flow@alpha hooks post-command --command "command"

# Pre-edit hook
npx claude-flow@alpha hooks pre-edit --file "file.js"

# Post-edit hook
npx claude-flow@alpha hooks post-edit --file "file.js"

# Session management
npx claude-flow@alpha hooks session-start
npx claude-flow@alpha hooks session-end --export-metrics true
npx claude-flow@alpha hooks session-restore --session-id "id"
```

### Neural Features
```bash
# Check neural status
npx claude-flow@alpha neural status

# Train patterns
npx claude-flow@alpha neural train --pattern "pattern"

# Get patterns
npx claude-flow@alpha neural patterns

# Predict
npx claude-flow@alpha neural predict --input "input"
```

## 🎭 Playwright MCP Commands

```javascript
// Navigation
mcp__playwright__playwright_navigate({ url: "https://example.com" })

// Screenshots
mcp__playwright__playwright_screenshot({ name: "screenshot", fullPage: true })

// Interactions
mcp__playwright__playwright_click({ selector: "#button" })
mcp__playwright__playwright_fill({ selector: "#input", value: "text" })
mcp__playwright__playwright_hover({ selector: "#element" })

// Browser control
mcp__playwright__playwright_go_back()
mcp__playwright__playwright_go_forward()
mcp__playwright__playwright_close()

// Console logs
mcp__playwright__playwright_console_logs({ type: "error" })

// HTTP operations
mcp__playwright__playwright_get({ url: "https://api.example.com" })
mcp__playwright__playwright_post({ url: "https://api.example.com", value: "{}" })
```

## 🌐 Browser MCP Commands

```javascript
// Navigation
mcp__browsermcp__browser_navigate({ url: "https://example.com" })
mcp__browsermcp__browser_go_back()
mcp__browsermcp__browser_go_forward()

// Page interactions
mcp__browsermcp__browser_snapshot()
mcp__browsermcp__browser_click({ selector: "#button" })
mcp__browsermcp__browser_type({ selector: "#input", text: "Hello" })
mcp__browsermcp__browser_hover({ selector: "#element" })

// Screenshots
mcp__browsermcp__browser_screenshot({ selector: "body" })

// Console
mcp__browsermcp__browser_get_console_logs()
```

## 📋 Task Master AI Commands

```javascript
// Project initialization
mcp__task-master-ai__initialize_project({ name: "Project", description: "Desc" })

// PRD parsing
mcp__task-master-ai__parse_prd({ prd: "PRD content" })

// Task management
mcp__task-master-ai__get_tasks()
mcp__task-master-ai__add_task({ title: "Task", description: "Desc" })
mcp__task-master-ai__update_task({ id: "task-id", updates: {} })
mcp__task-master-ai__set_task_status({ id: "task-id", status: "in_progress" })

// Task expansion
mcp__task-master-ai__expand_task({ id: "task-id" })
mcp__task-master-ai__expand_all()

// Complexity analysis
mcp__task-master-ai__analyze_project_complexity()
mcp__task-master-ai__complexity_report()

// Dependencies
mcp__task-master-ai__add_dependency({ from: "task1", to: "task2" })
mcp__task-master-ai__validate_dependencies()
```

## 🧘 Zen MCP Commands

```javascript
// AI-powered tools
mcp__zen__thinkdeep({ query: "Deep question" })
mcp__zen__planner({ task: "Plan this" })
mcp__zen__consensus({ options: ["option1", "option2"] })

// Code tools
mcp__zen__codereview({ code: "code to review" })
mcp__zen__debug({ error: "error message" })
mcp__zen__refactor({ code: "code to refactor" })
mcp__zen__testgen({ code: "code to test" })

// Security & docs
mcp__zen__secaudit({ code: "security review" })
mcp__zen__docgen({ code: "document this" })

// Analysis
mcp__zen__analyze({ data: "analyze this" })
mcp__zen__tracer({ execution: "trace this" })
```

## 📚 Context7 Commands

```javascript
// Library resolution
mcp__context7__resolve-library-id({ query: "react" })

// Documentation
mcp__context7__get-library-docs({ libraryId: "lib-id" })
```

## 🔧 Rube Commands

```javascript
// Planning
mcp__rube__RUBE_CREATE_PLAN({ goal: "Goal description" })

// Tool execution
mcp__rube__RUBE_MULTI_EXECUTE_TOOL({ tools: [...] })
mcp__rube__RUBE_SEARCH_TOOLS({ query: "tool search" })

// Remote operations
mcp__rube__RUBE_REMOTE_BASH_TOOL({ command: "ls -la" })
mcp__rube__RUBE_REMOTE_WORKBENCH()

// Connections
mcp__rube__RUBE_MANAGE_CONNECTIONS()
mcp__rube__RUBE_WAIT_FOR_CONNECTION({ timeout: 30 })
```

## 🔄 Claude Flow Integration Examples

### Example 1: Full Stack Development
```bash
# Initialize swarm
npx claude-flow@alpha swarm init --topology mesh --max-agents 5

# Spawn specialized agents
npx claude-flow@alpha agent spawn --type backend-dev
npx claude-flow@alpha agent spawn --type frontend-dev
npx claude-flow@alpha agent spawn --type tester
npx claude-flow@alpha agent spawn --type reviewer

# Orchestrate tasks
npx claude-flow@alpha task orchestrate --description "Build REST API with authentication"
```

### Example 2: SPARC TDD Workflow
```bash
# Run complete TDD cycle
npx claude-flow@alpha sparc tdd "User authentication system"

# Or run phases individually
npx claude-flow@alpha sparc run spec "User auth requirements"
npx claude-flow@alpha sparc run pseudocode "Auth algorithm"
npx claude-flow@alpha sparc run architect "System design"
npx claude-flow@alpha sparc run refinement "Implementation"
npx claude-flow@alpha sparc run completion "Integration"
```

### Example 3: Performance Optimization
```bash
# Analyze bottlenecks
npx claude-flow@alpha bottleneck analyze

# Optimize topology
npx claude-flow@alpha topology optimize --current mesh --target adaptive

# Monitor performance
npx claude-flow@alpha swarm monitor --metrics true
```

### Example 4: Memory-Driven Development
```bash
# Store design decisions
npx claude-flow@alpha memory store --key "architecture/auth" --value "JWT-based"

# Search previous decisions
npx claude-flow@alpha memory search --query "authentication"

# Restore session
npx claude-flow@alpha hooks session-restore --session-id "prev-session"
```

## 🚨 Important Notes

1. **Concurrent Execution**: Always batch multiple operations in single messages
2. **Hook Integration**: Hooks run automatically with file operations
3. **Memory Persistence**: Memory persists across sessions when enabled
4. **Token Optimization**: Use `--optimize-tokens` flag for large operations
5. **Dry Run**: Use `--dry-run` to test commands without execution

## 🔗 Quick Reference Links

- [Claude Flow Docs](https://github.com/ruvnet/claude-flow)
- [MCP Protocol Spec](https://modelcontextprotocol.io)
- [SPARC Methodology](https://github.com/ruvnet/claude-flow/docs/sparc)

---

💡 **Pro Tip**: Use `npx claude-flow@alpha help [command]` for detailed command help