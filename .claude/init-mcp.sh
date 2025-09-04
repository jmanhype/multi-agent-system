#!/bin/bash

# Claude MCP Server Initialization Script
# Ensures all MCP servers are properly configured and available

echo "🚀 Initializing Claude MCP Servers..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running in experiments directory
if [[ ! "$PWD" == *"/experiments"* ]]; then
    echo -e "${YELLOW}⚠️  Warning: Not in experiments directory${NC}"
fi

# Function to check if MCP server is available
check_mcp_server() {
    local server=$1
    echo -n "Checking $server... "
    
    if npx $server --version &>/dev/null || npx $server mcp --version &>/dev/null; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        return 1
    fi
}

# List of MCP servers to check
MCP_SERVERS=(
    "claude-flow@alpha"
    "ruv-swarm"
    "flow-nexus"
    "exa-mcp-server"
    "@modelcontextprotocol/server-playwright"
    "browser-mcp"
    "@upstash/context7-mcp"
    "task-master-ai"
    "zen-mcp"
    "rube-mcp"
    "apollo-dgraph-mcp"
    "apollo-dagger-mcp"
)

echo "📋 Checking MCP Server Availability:"
echo "===================================="

available_count=0
total_count=${#MCP_SERVERS[@]}

for server in "${MCP_SERVERS[@]}"; do
    if check_mcp_server "$server"; then
        ((available_count++))
    fi
done

echo ""
echo "📊 Summary: $available_count/$total_count servers available"

# Initialize claude-flow if available
if command -v npx &> /dev/null && npx claude-flow@alpha --version &>/dev/null; then
    echo ""
    echo "🔧 Initializing Claude Flow..."
    npx claude-flow@alpha init --silent 2>/dev/null || true
    
    # Check for swarm configuration
    if [ -f ".claude-flow/config.json" ]; then
        echo -e "${GREEN}✓ Claude Flow configuration found${NC}"
    else
        echo "Creating default Claude Flow configuration..."
        mkdir -p .claude-flow
        cat > .claude-flow/config.json << 'EOF'
{
  "version": "2.0.0",
  "swarm": {
    "defaultTopology": "mesh",
    "maxAgents": 10,
    "autoSpawn": true
  },
  "hooks": {
    "enabled": true,
    "autoFormat": true,
    "memoryPersistence": true
  },
  "performance": {
    "concurrent": true,
    "batchSize": 10,
    "cacheEnabled": true
  }
}
EOF
        echo -e "${GREEN}✓ Claude Flow configuration created${NC}"
    fi
fi

# Check environment variables
echo ""
echo "🔑 Checking Environment Variables:"
echo "=================================="

ENV_VARS=(
    "CLAUDE_FLOW_AUTO_COMMIT"
    "CLAUDE_FLOW_HOOKS_ENABLED"
    "CLAUDE_FLOW_CONCURRENT"
    "CLAUDE_FLOW_BATCH_OPERATIONS"
    "CLAUDE_FLOW_MAX_AGENTS"
)

for var in "${ENV_VARS[@]}"; do
    if [ -n "${!var}" ]; then
        echo -e "$var: ${GREEN}${!var}${NC}"
    else
        echo -e "$var: ${YELLOW}not set${NC}"
    fi
done

# Create hooks directory structure if missing
echo ""
echo "📁 Ensuring directory structure..."

REQUIRED_DIRS=(
    ".claude/agents"
    ".claude/hooks"
    ".claude/mcp"
    ".claude/checkpoints"
    ".claude/commands"
    ".claude/helpers"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo -e "Created: $dir"
    fi
done

echo ""
echo -e "${GREEN}✅ MCP initialization complete!${NC}"
echo ""
echo "💡 Quick Commands:"
echo "  • Start swarm: npx claude-flow@alpha swarm init --topology mesh"
echo "  • Spawn agent: npx claude-flow@alpha agent spawn --type coder"
echo "  • Run SPARC: npx claude-flow sparc run <mode> '<task>'"
echo "  • List agents: npx claude-flow@alpha agent list"
echo ""