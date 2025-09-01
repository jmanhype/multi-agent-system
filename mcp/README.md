# MCP (Model Context Protocol) Directory

## Overview

The MCP directory contains Model Context Protocol configurations, server definitions, and integration settings for connecting the multi-agent system with various LLM providers and services.

## Directory Structure

```
mcp/
├── servers.json       # MCP server configurations
├── clients.yaml      # Client configurations
├── integration.json  # Integration settings
├── registry.yaml     # Service registry
└── servers/          # Server-specific configs
    ├── data/        # Data server configs
    ├── exec/        # Execution server configs
    ├── repo/        # Repository server configs
    └── search/      # Search server configs
```

## MCP Servers

### Configured Servers
- **Claude Flow**: Multi-agent orchestration
- **Playwright**: Browser automation
- **Context7**: Documentation retrieval
- **Dgraph**: Graph database operations
- **Dagger**: CI/CD pipeline execution
- **Ruv Swarm**: Distributed swarm operations
- **Exa**: Web search capabilities
- **Rube**: Cross-app automation
- **Task Master**: Task management
- **Zen**: AI model coordination
- **Apollo**: GraphQL operations
- **BrowserMCP**: Browser control

## Configuration Examples

### Server Configuration
```json
{
  "servers": {
    "claude-flow": {
      "path": "/path/to/claude-flow",
      "env": {
        "API_KEY": "${CLAUDE_API_KEY}"
      }
    }
  }
}
```

### Client Configuration
```yaml
clients:
  default:
    timeout: 30000
    retries: 3
    backoff: exponential
```

## Integration Points

- LLM providers
- External services
- Database connections
- API gateways
- Authentication services

## Best Practices

- Secure credential storage
- Environment-based configs
- Connection pooling
- Error handling
- Rate limiting
- Monitoring

---

For detailed MCP documentation, refer to server-specific configs and CLAUDE.md.
