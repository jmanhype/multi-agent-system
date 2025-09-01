# MCP Configuration Directory

## Purpose
Model Context Protocol configuration for tool coordination.

## Allowed Operations
- ✅ Read all MCP configurations
- ✅ Update client settings and timeouts
- ✅ Add new MCP server definitions
- ⚠️ Modify existing server configs with validation
- ❌ Remove core MCP servers

## Configuration Files
- `clients.yaml` - MCP client configuration
- `servers.json` - Server definitions (if present)
- `integration.json` - Cross-integration settings

## Primary Agents
- `system-architect` - MCP architecture design
- `api-docs` - MCP documentation
- `cicd-engineer` - MCP testing and validation

## Client Configuration
Manages:
- Connection timeouts and retries
- Transport protocols (stdio, HTTP)
- Connection pooling
- Rate limiting
- Error handling

## Server Integration
Coordinates:
- Tool discovery and registration
- Schema validation
- Version compatibility
- Health monitoring

## Best Practices
1. Always validate new server configs
2. Test connections before deployment
3. Use appropriate timeouts for operations
4. Monitor MCP server health
5. Document custom integrations

## Troubleshooting
- Check server availability with health checks
- Validate schema compatibility
- Review connection logs
- Test with minimal configurations