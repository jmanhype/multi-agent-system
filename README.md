# Multi-Agent System for Claude Code
## Powered by Claude-Flow v2.0.0 Alpha

A comprehensive AI agent orchestration framework built on [Claude-Flow v2.0.0 Alpha](https://github.com/ruvnet/claude-flow) - the revolutionary AI swarm orchestration platform. This implementation extends Claude Code CLI with enterprise-grade hive-mind intelligence, neural pattern recognition, and 87+ MCP tools for unprecedented AI-powered development workflows.

## 🚀 Overview

This framework leverages Claude-Flow's powerful swarm orchestration capabilities to provide:
- **Hive-Mind Intelligence**: Queen-led AI coordination with 64 specialized worker agents
- **Neural Networks**: 27+ cognitive models with WASM SIMD acceleration
- **MCP Integration**: 87 comprehensive tools for swarm orchestration, memory, and automation
- **Performance Metrics**: 84.8% SWE-Bench solve rate, 32.3% token reduction, 2.8-4.4x speed improvement

Built specifically for Claude Code's terminal-based interface with seamless MCP integration and natural language command processing.

## ✨ Key Features

### Claude-Flow v2 Alpha Core Capabilities
- **64 Specialized AI Agents**: Complete agent ecosystem across 16 categories
- **Hive-Mind Architecture**: Queen-led coordination with worker specialization
- **Neural Pattern Recognition**: 27+ cognitive models for advanced reasoning
- **SQLite Memory System**: Persistent `.swarm/memory.db` with 12 specialized tables
- **WASM SIMD Acceleration**: High-performance neural network operations

### Swarm Intelligence & Coordination
- **Swarm Topologies**: Hierarchical, mesh, ring, and star configurations
- **Dynamic Self-Organization**: Agents adapt and reorganize based on task requirements
- **Fault Tolerance**: Automatic failover and recovery mechanisms
- **Consensus Protocols**: Raft, Byzantine, CRDT, Gossip implementations
- **Performance Metrics**: 84.8% SWE-Bench solve rate with 2.8-4.4x speed improvement

### Automated Hooks & CI/CD
- **Pre-run Hooks**: Automatic linting, type checking, and unit testing for Python, Node.js, Rust, and Elixir projects
- **Post-run Hooks**: Execution analysis and review generation
- **Verification Gates**: Truth score verification and security checks
- **Hook Logging**: Comprehensive JSON logs for chat, tool use (pre/post), and agent lifecycle events

### Specialized Agent Types

#### Core Agents
- **Planner**: Strategic planning and task breakdown
- **Researcher**: Information gathering and analysis  
- **Coder**: Implementation and code generation
- **Tester**: Testing with production validation
- **Reviewer**: Multi-perspective code review

#### Performance & Optimization Agents
- **Performance Monitor**: Real-time metrics, bottleneck analysis, SLA monitoring
- **Performance Benchmarker**: Consensus performance testing
- **Load Balancer**: Dynamic resource distribution
- **Topology Optimizer**: Swarm configuration optimization
- **Resource Allocator**: Intelligent resource management

#### Consensus & Coordination Agents
- **Byzantine Coordinator**: Byzantine fault-tolerant consensus
- **Raft Manager**: Raft consensus protocol implementation
- **CRDT Synchronizer**: Conflict-free replicated data types
- **Gossip Coordinator**: Gossip protocol for distributed systems
- **Quorum Manager**: Quorum-based decision making
- **Security Manager**: Consensus security protocols

#### GitHub Integration Agents
- **PR Manager**: Pull request automation
- **Issue Tracker**: Intelligent issue management
- **Release Manager & Coordinator**: Release automation
- **Code Review Swarm**: Distributed code review
- **Multi-Repo Swarm**: Cross-repository coordination
- **Workflow Automation**: GitHub Actions integration

#### Advanced Capabilities
- **Hive Mind**: Distributed intelligence with shared memory, consensus mechanisms, and session management
- **SPARC Methodology**: Complete SPARC implementation (Specification → Pseudocode → Architecture → Refinement → Code)
- **Adaptive Coordinator**: Dynamic strategy adjustment based on performance metrics
- **Memory Persistence**: Cross-session knowledge retention with memory stores

## 📁 Project Structure

```
.
├── agents/           # Agent templates and configurations
│   ├── core/        # Core agent types (planner, coder, etc.)
│   ├── github/      # GitHub-specific agents
│   ├── consensus/   # Consensus and coordination agents
│   ├── optimization/# Performance and optimization agents
│   └── swarm/       # Swarm coordination templates
├── commands/        # Command definitions for agent operations
├── workflows/       # Pre-defined automation workflows
├── hooks/          # Event hooks for agent lifecycle
├── helpers/        # Utility scripts and tools
├── mcp/           # Model Context Protocol integration
└── docs/          # Documentation and references
```

## 🔧 Installation & Setup

### Prerequisites
- Claude Code CLI installed (`npm install -g @anthropic/claude-code` or native install)
- Active Claude Code account (run `claude --login` if needed)
- Node.js 18+ for Claude-Flow integration

### Quick Install with Claude-Flow

```bash
# Install Claude-Flow Alpha globally
npm install -g claude-flow@alpha

# Initialize in your project with enhanced MCP setup
npx claude-flow@alpha init --force

# Clone this framework configuration
git clone https://github.com/jmanhype/multi-agent-system.git .claude
cd .claude

# Initialize MCP servers including Claude-Flow
./init-mcp.sh
```

### Launch Options

```bash
# Quick AI coordination (simple tasks)
npx claude-flow@alpha swarm "your task here" --claude

# Full hive-mind system (complex projects)
npx claude-flow@alpha hive-mind wizard

# Standard Claude Code with framework
claude
```

**Quick Rule**: Start with `swarm` for most tasks. Use `hive-mind` when you need persistent sessions or complex multi-agent coordination.

## 🎯 Quick Start with Claude Code

### 🔴 IMPORTANT: System Activation

To activate the multi-agent system in Claude Code, you need to use the **Task tool** to spawn agents:

```markdown
⏺ In Claude Code, request agent activation:
"Use the Task tool to spawn test generation agents"
"Deploy TDD agents via Task tool for the API"
"Activate hive-mind system using Task tool"
```

The Task tool is the primary mechanism for agent orchestration in Claude Code. Example workflow:

```markdown
⏺ Update Todos
  ⎿  ☒ API development and documentation              
     ☐ Testing suite with TDD approach
     ☐ Use Task tool for test generation
     ☐ Deploy test agents via Task tool
     ☐ E2E tests via Task tool agents
```

#### How It Works: One Command, Full Activation

**In a fresh Claude Code instance, a single Task tool command activates the entire system:**

```markdown
"Use the Task tool to dogfood our multi-agent system by creating a full-stack app"
```

This single natural language request triggers:

1. **Claude-Flow MCP Server** (priority 1) initialization
2. **Automatic Agent Spawning** - All 64 specialized agents as needed:
   - Planner agents for strategy
   - Researcher agents for best practices
   - Architect agents for system design
   - Developer agents for implementation
   - Tester agents for validation
   - DevOps agents for CI/CD
3. **Hook Chain Activation** - All automation hooks fire automatically
4. **Hive-Mind Coordination** - Queen-led orchestration with worker specialization
5. **Memory Persistence** - Decisions saved across sessions

**No manual configuration needed** - The Task tool acts as a universal adapter between Claude Code's interface and the complex multi-agent system, handling all orchestration automatically.

### Using Slash Commands
After activation, the framework integrates with Claude Code's slash command system:

```bash
# In Claude Code terminal
/swarm-init mesh 5
# Initializes a mesh topology with 5 agents

/agent-spawn reviewer
# Spawns a specialized code review agent

/task-orchestrate "Refactor authentication module"
# Orchestrates task across available agents
```

### Natural Language Commands
Simply describe what you want in plain English:

```bash
# In Claude Code
"Initialize a swarm of agents to review and refactor the authentication module"
"Create a performance monitoring dashboard for the current codebase"
"Set up automated testing hooks for all Python files"
```

### Using with MCP Servers
The framework leverages Claude Code's MCP integration:

```bash
# Access through MCP tools
"Use the swarm coordinator to analyze code quality"
"Deploy consensus agents for architectural decisions"
"Enable performance monitoring for all active agents"
```

## 📚 Use Cases

### Automated Code Review
Deploy a swarm of specialized reviewers to analyze code from multiple perspectives:
- Security analysis
- Performance optimization
- Code quality assessment
- Best practices validation

### Complex Problem Solving
Break down complex problems and distribute them across expert agents:
- Research agents gather information
- Architects design solutions
- Coders implement features
- Testers validate results

### CI/CD Automation
Integrate with GitHub for automated workflows:
- PR review and enhancement
- Issue triage and assignment
- Release coordination
- Multi-repo synchronization

## 🛠️ Advanced Claude Code Features

### Custom Commands (.claude/commands)
Store frequently used prompts as markdown files:
```bash
# Creates reusable slash commands
echo "Review this code for security issues" > .claude/commands/security-review.md
# Use in Claude Code: /security-review
```

### Hook Integration
Automated workflows that trigger on Claude Code events:
```bash
# Pre-run validation
.claude/hooks/pre_run.sh
# Post-execution analysis
.claude/hooks/post_run.sh
# Verification gates
.claude/hooks/verify_gate.sh
```

### MCP Server Configuration
The framework includes pre-configured MCP servers for Claude Code:
- **File Operations**: Direct file manipulation
- **Search**: Advanced codebase search
- **Execution**: Safe command execution
- **GitHub Integration**: PR and issue management
- **Swarm Coordination**: Multi-agent orchestration

Configure additional servers in `.claude/mcp/servers.json`.

### Performance Monitoring Dashboard
Real-time metrics visible in Claude Code:
```bash
# Launch monitoring
/performance-monitor
# View agent metrics
/agent-metrics
# Check swarm status
/swarm-status
```

## 💡 Claude Code Tips & Best Practices

### Optimize Token Usage
- Use `/clear` frequently to reset context when starting new tasks
- Enable `--dangerously-skip-permissions` for automated workflows (use with caution)
- Navigate history with up arrow or double-Escape for message list

### File Management
- Hold Shift while dragging files to reference them properly
- Use tab-completion for quick file/folder references
- Store large contexts in `.claude/commands/` for reuse

### Model Selection
- Default: Opus (complex tasks) → Sonnet (after 50% usage)
- Use `/model opus` for complex architecture decisions
- Use `/model sonnet` for quick implementations

### Session Management
- Credentials stored locally after `/login`
- Sessions persist across terminal restarts
- Use continuation IDs for long-running tasks

## 📖 Documentation

### Claude Code Resources
- [Official Claude Code Docs](https://docs.anthropic.com/en/docs/claude-code/overview)
- [Claude Code Quickstart](https://docs.anthropic.com/en/docs/claude-code/quickstart)
- [MCP Integration Guide](https://docs.anthropic.com/en/docs/claude-code/mcp)

### Framework Documentation
- [Command Reference](docs/MCP_COMMANDS_REFERENCE.md)
- [Agent Templates](agents/README.md)
- [Workflow Examples](workflows/example-workflows.md)
- [Hook System](hooks/README.md)

## 🤝 Contributing

Contributions are welcome! This framework is designed to extend Claude Code's capabilities. Please:
- Follow Claude Code conventions for slash commands
- Test with multiple Claude models
- Document MCP server requirements
- Include example usage in natural language

## 📄 License

This project is open source and available under the MIT License.

## 🔗 Links

### Project Resources
- [Repository](https://github.com/jmanhype/multi-agent-system)
- [Issues](https://github.com/jmanhype/multi-agent-system/issues)

### Claude-Flow Resources
- [Claude-Flow v2.0.0 Alpha](https://github.com/ruvnet/claude-flow)
- [Claude-Flow Wiki](https://github.com/ruvnet/claude-flow/wiki)
- [Installation Guide](https://github.com/ruvnet/claude-flow/wiki/Installation-Guide)
- [Agent System Overview](https://github.com/ruvnet/claude-flow/wiki/Agent-System-Overview)

### Claude Code Resources
- [Claude Code Official](https://claude.ai/code)
- [Claude Code Docs](https://docs.anthropic.com/en/docs/claude-code/overview)
- [Claude Developers Discord](https://discord.gg/claude-dev)

---

**Built on Claude-Flow v2.0.0 Alpha** - The revolutionary AI swarm orchestration platform for Claude Code CLI. This framework provides enterprise-grade hive-mind intelligence, neural pattern recognition, and comprehensive MCP integration for unprecedented AI-powered development workflows.