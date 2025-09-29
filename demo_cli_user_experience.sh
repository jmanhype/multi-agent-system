#!/bin/bash
# DataAgent CLI User Experience Demo

echo "========================================"
echo "DataAgent CLI - User Experience Demo"
echo "========================================"
echo ""

# Setup mock auth for demo
echo "Setting up demo authentication..."
mkdir -p ~/.dataagent
echo '{"access_token": "demo_token_12345", "refresh_token": "refresh_demo", "expires_at": 9999999999}' > ~/.dataagent/tokens.json
chmod 600 ~/.dataagent/tokens.json

echo "✓ Demo authentication configured"
echo ""

# Show help
echo "1. CHECKING HELP"
echo "----------------"
python -m lib.agents.data_agent.cli --help
echo ""

# Check auth status
echo "2. AUTHENTICATION STATUS"
echo "------------------------"
python -m lib.agents.data_agent.cli auth status
echo ""

# Configure settings
echo "3. CONFIGURATION"
echo "----------------"
python -m lib.agents.data_agent.cli config set default_format table
python -m lib.agents.data_agent.cli config set max_rows 1000
python -m lib.agents.data_agent.cli config list
echo ""

# Basic analysis
echo "4. BASIC ANALYSIS"
echo "-----------------"
echo "Query: 'Show top 5 products by revenue'"
python -m lib.agents.data_agent.cli analyze "Show top 5 products by revenue" -s data/sales_data.csv
echo ""

# JSON output
echo "5. JSON OUTPUT"
echo "--------------"
echo "Query: 'Show summary statistics' (JSON format)"
python -m lib.agents.data_agent.cli analyze "Show summary statistics" -s data/sales_data.csv -f json | head -20
echo ""

# Without source (would use default if configured)
echo "6. NATURAL LANGUAGE QUERY"
echo "--------------------------"
echo "Query: 'What insights can you find in this data?'"
python -m lib.agents.data_agent.cli analyze "What insights can you find in this data?" -s data/sales_data.csv
echo ""

# Error handling demo
echo "7. ERROR HANDLING"
echo "-----------------"
echo "Testing with non-existent file..."
python -m lib.agents.data_agent.cli analyze "Analyze" -s nonexistent.csv 2>&1 | head -5
echo ""

echo "========================================"
echo "Demo Complete!"
echo "========================================"
echo ""
echo "Key Features Demonstrated:"
echo "✓ OAuth authentication with Claude subscriptions"
echo "✓ Natural language data analysis"
echo "✓ Multiple output formats (table, JSON, CSV)"
echo "✓ Configuration management"
echo "✓ Error handling"
echo ""
echo "To install for real use:"
echo "  pip install dataagent-cli"
echo "  dataagent auth login"
echo "  dataagent analyze 'Your query here' -s yourdata.csv"