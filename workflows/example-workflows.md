# 🎯 Example MCP Workflows

## 🚀 Workflow 1: Full Stack Application Development

### Objective
Build a complete web application with backend API, frontend UI, and database.

### Steps
```bash
# 1. Initialize project structure
mkdir -p app/{backend,frontend,database,tests,docs}

# 2. Start swarm coordination
npx claude-flow@alpha swarm init --topology mesh --max-agents 6

# 3. Spawn specialized agents (via Claude Code Task tool)
# In Claude: Use Task tool to spawn agents concurrently:
# - Task("Backend API", "Build Express REST API", "backend-dev")
# - Task("Frontend", "Create React UI", "coder")
# - Task("Database", "Design PostgreSQL schema", "code-analyzer")
# - Task("Tests", "Write comprehensive tests", "tester")
# - Task("Docs", "Generate API documentation", "api-docs")
# - Task("Review", "Code quality review", "reviewer")

# 4. Monitor progress
npx claude-flow@alpha swarm monitor

# 5. Check results
npx claude-flow@alpha agent metrics
```

## 🧪 Workflow 2: Test-Driven Development (TDD)

### Objective
Implement a new feature using SPARC TDD methodology.

### Steps
```bash
# 1. Define the feature
FEATURE="User authentication with JWT"

# 2. Run complete TDD workflow
npx claude-flow@alpha sparc tdd "$FEATURE"

# OR run phases individually:

# 3a. Specification phase
npx claude-flow@alpha sparc run spec "$FEATURE requirements"

# 3b. Pseudocode design
npx claude-flow@alpha sparc run pseudocode "$FEATURE algorithm"

# 3c. Architecture
npx claude-flow@alpha sparc run architect "$FEATURE system design"

# 3d. Refinement (implementation)
npx claude-flow@alpha sparc run refinement "$FEATURE implementation"

# 3e. Completion (integration)
npx claude-flow@alpha sparc run completion "$FEATURE integration"

# 4. Run tests
npm test
```

## 🌐 Workflow 3: Web Scraping & Analysis

### Objective
Scrape website data and analyze it using AI.

### Using Playwright MCP
```javascript
// In Claude, use these MCP tools:

// 1. Navigate to website
mcp__playwright__playwright_navigate({ 
    url: "https://example.com",
    headless: false 
})

// 2. Take screenshot
mcp__playwright__playwright_screenshot({ 
    name: "homepage",
    fullPage: true 
})

// 3. Extract text
mcp__playwright__playwright_get_visible_text()

// 4. Analyze with Zen
mcp__zen__analyze({ 
    data: extractedText,
    query: "Summarize key insights" 
})

// 5. Generate report
mcp__zen__docgen({ 
    content: analysis,
    format: "markdown" 
})
```

## 📊 Workflow 4: Project Management from PRD

### Objective
Parse a Product Requirements Document and create task breakdown.

### Steps
```javascript
// 1. Initialize project
mcp__task-master-ai__initialize_project({
    name: "E-Commerce Platform",
    description: "Full-featured online store"
})

// 2. Parse PRD
mcp__task-master-ai__parse_prd({
    prd: "PRD content here..."
})

// 3. Analyze complexity
mcp__task-master-ai__analyze_project_complexity()

// 4. Expand all tasks
mcp__task-master-ai__expand_all()

// 5. Generate report
mcp__task-master-ai__complexity_report()

// 6. Set up dependencies
mcp__task-master-ai__validate_dependencies()
```

## 🔍 Workflow 5: Code Review & Refactoring

### Objective
Review existing code and refactor for better quality.

### Steps
```javascript
// 1. Analyze codebase with Zen
mcp__zen__analyze({
    path: "./src",
    metrics: true
})

// 2. Deep code review
mcp__zen__codereview({
    files: ["./src/main.js", "./src/utils.js"],
    level: "comprehensive"
})

// 3. Security audit
mcp__zen__secaudit({
    path: "./src",
    includeDepencies: true
})

// 4. Generate refactoring plan
mcp__zen__refactor({
    code: problemCode,
    principles: ["SOLID", "DRY", "KISS"]
})

// 5. Generate tests
mcp__zen__testgen({
    code: refactoredCode,
    coverage: "comprehensive"
})
```

## 🤖 Workflow 6: AI-Powered Development Assistant

### Objective
Use AI to help with complex development decisions.

### Steps
```javascript
// 1. Deep thinking for architecture
mcp__zen__thinkdeep({
    query: "What's the best architecture for a real-time chat app?"
})

// 2. Planning implementation
mcp__zen__planner({
    task: "Implement WebSocket-based chat with Redis pub/sub"
})

// 3. Consensus on technical choices
mcp__zen__consensus({
    question: "Which database for chat history?",
    options: ["PostgreSQL", "MongoDB", "Cassandra"]
})

// 4. Debug issues
mcp__zen__debug({
    error: "WebSocket connection dropping after 30 seconds",
    context: connectionCode
})
```

## 🔄 Workflow 7: Continuous Integration Setup

### Objective
Set up automated CI/CD pipeline.

### Steps
```bash
# 1. Initialize swarm for DevOps
npx claude-flow@alpha swarm init --topology star --max-agents 3

# 2. Create pipeline configuration (via Task tool)
# Task("CI Setup", "Create GitHub Actions workflow", "cicd-engineer")
# Task("Docker", "Containerize application", "backend-dev")
# Task("Tests", "Set up test automation", "tester")

# 3. Monitor setup progress
npx claude-flow@alpha swarm monitor

# 4. Validate pipeline
npx claude-flow@alpha hooks pre-command --command "gh workflow run ci"
```

## 🧠 Workflow 8: Memory-Driven Development

### Objective
Use persistent memory for consistent development patterns.

### Steps
```bash
# 1. Store architectural decisions
npx claude-flow@alpha memory store \
    --key "architecture/database" \
    --value "PostgreSQL with Redis cache"

# 2. Store coding standards
npx claude-flow@alpha memory store \
    --key "standards/naming" \
    --value "camelCase for JS, snake_case for Python"

# 3. Search previous decisions
npx claude-flow@alpha memory search --query "authentication"

# 4. Use in development
# Memory is automatically loaded for agents via hooks

# 5. Export memory for team sharing
npx claude-flow@alpha memory export --file team-memory.json
```

## ⚡ Workflow 9: Performance Optimization

### Objective
Identify and fix performance bottlenecks.

### Steps
```bash
# 1. Run performance analysis
npx claude-flow@alpha performance report

# 2. Identify bottlenecks
npx claude-flow@alpha bottleneck analyze

# 3. Optimize topology
npx claude-flow@alpha topology optimize \
    --current mesh \
    --workload "data-processing"

# 4. Benchmark improvements
npx claude-flow@alpha benchmark run \
    --before optimization \
    --after optimization \
    --iterations 100

# 5. Monitor token usage
npx claude-flow@alpha token usage --detailed
```

## 🎨 Workflow 10: UI Component Development

### Objective
Build reusable UI components with documentation.

### Using multiple MCP tools together:
```javascript
// 1. Plan component architecture
mcp__zen__planner({
    task: "Design component library structure"
})

// 2. Generate component
// Via Task tool:
// Task("Component Dev", "Create Button, Card, Modal components", "coder")

// 3. Generate Storybook stories
// Task("Stories", "Create Storybook stories", "coder")

// 4. Screenshot components
mcp__playwright__playwright_navigate({ url: "http://localhost:6006" })
mcp__playwright__playwright_screenshot({ name: "component-library" })

// 5. Generate documentation
mcp__zen__docgen({
    components: ["Button", "Card", "Modal"],
    format: "markdown"
})
```

## 📝 Tips for Effective Workflows

1. **Always batch operations** - Use single messages for multiple tasks
2. **Use appropriate topology** - Mesh for collaboration, Star for centralized
3. **Monitor progress** - Regular `swarm monitor` checks
4. **Persist important data** - Use memory system for continuity
5. **Optimize tokens** - Use `--optimize-tokens` for large operations
6. **Test incrementally** - Run tests after each major step
7. **Document decisions** - Store in memory for future reference

## 🔗 Combining MCP Tools

Best practices for tool combination:
- **Claude Flow + Playwright**: Web automation with AI coordination
- **Task Master + Zen**: Project planning with deep analysis
- **Context7 + Memory**: Documentation with persistent storage
- **Rube + Browser MCP**: Complex automation workflows

---

💡 Remember: The power of MCP comes from combining tools effectively!