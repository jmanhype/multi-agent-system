# Multi-Agent System for Claude Code

A comprehensive AI agent orchestration framework designed specifically for Claude Code CLI, providing advanced multi-agent coordination, automated workflows, and distributed task management for complex software engineering projects.

## 🚀 Overview

This framework extends Claude Code's capabilities with a sophisticated multi-agent system featuring real-time performance monitoring, automated hooks, consensus mechanisms, and specialized agent templates. Built to leverage Claude Code's terminal-based interface, MCP integration, and natural language command processing.

## ✨ Key Features

### Agent Orchestration & Performance
- **Swarm Topologies**: Hierarchical, mesh, ring, and star configurations with adaptive coordination
- **Performance Monitor Agent**: Real-time metrics collection, SLA monitoring, anomaly detection
- **Resource Tracking**: Multi-dimensional metrics for system, agent, coordination, and task execution
- **Dynamic Scaling & Load Balancing**: Automatic topology optimization based on workload
- **Consensus Mechanisms**: Raft, Byzantine fault tolerance, CRDT synchronization, Gossip protocols

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

## 🔧 Installation & Setup for Claude Code

### Prerequisites
- Claude Code CLI installed (`npm install -g @anthropic/claude-code` or native install)
- Active Claude Code account (run `claude --login` if needed)
- Git repository initialized

### Setup Steps

1. Clone this framework into your `.claude` directory:
```bash
# In your project root
git clone https://github.com/jmanhype/multi-agent-system.git .claude
cd .claude
```

2. Initialize MCP servers for Claude Code:
```bash
./init-mcp.sh
# This configures MCP servers for file operations, search, and integrations
```

3. Configure Claude Code settings:
```bash
cp settings.json settings.local.json
# Edit settings.local.json with your preferences
```

4. Launch Claude Code with the framework:
```bash
# From your project root
claude
# The framework is now available through slash commands
```

## 🎯 Quick Start with Claude Code

### Using Slash Commands
The framework integrates with Claude Code's slash command system:

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

- [Repository](https://github.com/jmanhype/multi-agent-system)
- [Issues](https://github.com/jmanhype/multi-agent-system/issues)
- [Claude Code Official](https://claude.ai/code)
- [Claude Developers Discord](https://discord.gg/claude-dev)

---

Built specifically for Claude Code CLI. Enhances Claude's terminal-based coding assistant with multi-agent orchestration, automated workflows, and distributed task management.