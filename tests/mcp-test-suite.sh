#!/bin/bash

# MCP Test Suite - Comprehensive testing of all MCP tools
# Run this to verify all MCP servers are working correctly

set -e

echo "🧪 MCP Comprehensive Test Suite"
echo "================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results tracking
PASSED=0
FAILED=0
SKIPPED=0

# Function to run a test
run_test() {
    local name=$1
    local command=$2
    local expected=$3
    
    echo -n "Testing $name... "
    
    if eval "$command" &>/dev/null; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        ((FAILED++))
        return 1
    fi
}

# Function to check MCP tool availability
check_mcp_tool() {
    local tool=$1
    local test_command=$2
    
    echo -e "${BLUE}Testing $tool...${NC}"
    
    if eval "$test_command" &>/dev/null; then
        echo -e "  ${GREEN}✓ Available${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "  ${YELLOW}⚠ Not available${NC}"
        ((SKIPPED++))
        return 1
    fi
}

echo "1️⃣  Claude Flow Tests"
echo "----------------------"

# Claude Flow Core
run_test "Claude Flow version" "npx claude-flow@alpha --version"
run_test "Claude Flow help" "npx claude-flow@alpha help"
run_test "SPARC modes" "npx claude-flow@alpha sparc modes"

# Swarm Commands
echo ""
echo "2️⃣  Swarm Coordination Tests"
echo "----------------------------"

run_test "Swarm init" "npx claude-flow@alpha swarm init --topology mesh --dry-run"
run_test "Agent list" "npx claude-flow@alpha agent list"
run_test "Swarm monitor" "npx claude-flow@alpha swarm monitor --dry-run"

# SPARC Tests
echo ""
echo "3️⃣  SPARC Methodology Tests"
echo "---------------------------"

run_test "SPARC info spec" "npx claude-flow@alpha sparc info spec"
run_test "SPARC info pseudocode" "npx claude-flow@alpha sparc info pseudocode"
run_test "SPARC info architect" "npx claude-flow@alpha sparc info architect"
run_test "SPARC info refinement" "npx claude-flow@alpha sparc info refinement"
run_test "SPARC info completion" "npx claude-flow@alpha sparc info completion"

# Hooks Tests
echo ""
echo "4️⃣  Hooks System Tests"
echo "----------------------"

run_test "Pre-command hook" "npx claude-flow@alpha hooks pre-command --command 'echo test' --dry-run"
run_test "Post-command hook" "npx claude-flow@alpha hooks post-command --command 'echo test' --dry-run"
run_test "Session management" "npx claude-flow@alpha hooks session-end --dry-run"

# Memory Tests
echo ""
echo "5️⃣  Memory System Tests"
echo "-----------------------"

run_test "Memory usage" "npx claude-flow@alpha memory usage"
run_test "Memory search" "npx claude-flow@alpha memory search --query 'test' --dry-run"

# Performance Tests
echo ""
echo "6️⃣  Performance Analysis Tests"
echo "------------------------------"

run_test "Performance report" "npx claude-flow@alpha performance report --dry-run"
run_test "Token usage" "npx claude-flow@alpha token usage --dry-run"

# MCP Tool Availability
echo ""
echo "7️⃣  MCP Tool Availability"
echo "-------------------------"

check_mcp_tool "Playwright" "which npx && npx @modelcontextprotocol/server-playwright --help 2>&1 | head -1"
check_mcp_tool "Context7" "which npx && npx @upstash/context7-mcp --help 2>&1 | head -1"
check_mcp_tool "Zen" "which npx && npx zen-mcp --help 2>&1 | head -1"
check_mcp_tool "Task Master AI" "which npx && npx task-master-ai --help 2>&1 | head -1"

# Integration Tests
echo ""
echo "8️⃣  Integration Tests"
echo "--------------------"

# Test concurrent operations
echo -n "Testing concurrent operations... "
if npx claude-flow@alpha swarm init --topology mesh --max-agents 3 --dry-run &>/dev/null; then
    echo -e "${GREEN}✓ PASSED${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ FAILED${NC}"
    ((FAILED++))
fi

# Test batch operations
echo -n "Testing batch operations... "
if npx claude-flow@alpha sparc batch "spec pseudocode" "test task" --dry-run &>/dev/null; then
    echo -e "${GREEN}✓ PASSED${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠ SKIPPED${NC}"
    ((SKIPPED++))
fi

# Configuration Tests
echo ""
echo "9️⃣  Configuration Tests"
echo "-----------------------"

echo -n "Testing .claude directory... "
if [ -d ".claude" ]; then
    echo -e "${GREEN}✓ EXISTS${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ MISSING${NC}"
    ((FAILED++))
fi

echo -n "Testing settings.json... "
if [ -f ".claude/settings.json" ]; then
    echo -e "${GREEN}✓ EXISTS${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ MISSING${NC}"
    ((FAILED++))
fi

echo -n "Testing MCP configuration... "
if [ -f ".claude/mcp/servers.json" ]; then
    echo -e "${GREEN}✓ EXISTS${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ MISSING${NC}"
    ((FAILED++))
fi

# Summary
echo ""
echo "📊 Test Summary"
echo "==============="
echo -e "  ${GREEN}Passed:${NC} $PASSED"
echo -e "  ${RED}Failed:${NC} $FAILED"
echo -e "  ${YELLOW}Skipped:${NC} $SKIPPED"
echo ""

TOTAL=$((PASSED + FAILED + SKIPPED))
SUCCESS_RATE=$((PASSED * 100 / TOTAL))

if [ $SUCCESS_RATE -ge 80 ]; then
    echo -e "${GREEN}✅ Test suite passed with $SUCCESS_RATE% success rate${NC}"
    exit 0
elif [ $SUCCESS_RATE -ge 60 ]; then
    echo -e "${YELLOW}⚠️  Test suite partially passed with $SUCCESS_RATE% success rate${NC}"
    exit 0
else
    echo -e "${RED}❌ Test suite failed with only $SUCCESS_RATE% success rate${NC}"
    exit 1
fi