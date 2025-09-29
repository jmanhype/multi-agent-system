# DataAgent CLI

Natural language data analysis powered by your existing Claude subscription. No API keys required!

## 🚀 QuickStart (30 seconds)

```bash
# Install
pip install dataagent-cli

# Authenticate with your Claude subscription
dataagent auth login

# Analyze data with natural language
dataagent analyze "Show me the top 10 customers by revenue" -s sales.csv
```

That's it! You're now analyzing data with the power of Claude.

## Installation

### From PyPI
```bash
pip install dataagent-cli
```

### From Source
```bash
git clone https://github.com/jmanhype/multi-agent-system
cd multi-agent-system
pip install -e .
```

## Authentication

DataAgent uses OAuth to leverage your existing Claude subscription:

```bash
# First-time setup
dataagent auth login

# Check authentication status
dataagent auth status

# Logout when done
dataagent auth logout
```

No API keys to manage, no additional costs!

## Basic Usage

### Analyze Files

```bash
# CSV files
dataagent analyze "What are the main trends?" -s data.csv

# Excel files
dataagent analyze "Summarize the Q4 results" -s report.xlsx

# JSON data
dataagent analyze "Find anomalies" -s logs.json
```

### Query Databases

```bash
# PostgreSQL
dataagent analyze "Show monthly revenue" -s postgresql://localhost/sales

# MySQL
dataagent analyze "Customer segmentation" -s mysql://localhost/customers

# SQLite
dataagent analyze "Product performance" -s sqlite:///data.db
```

### Output Formats

```bash
# Table (default)
dataagent analyze "Top products" -s data.csv

# JSON
dataagent analyze "Sales summary" -s data.csv -f json

# CSV
dataagent analyze "Customer list" -s database.db -f csv -o customers.csv

# Charts
dataagent analyze "Plot trends over time" -s data.csv -f chart
```

## Interactive Mode

Start an interactive session for exploratory analysis:

```bash
dataagent interactive
```

Commands in interactive mode:
- `load <source>` - Load a data source
- `status` - Show current session info
- `help` - Show available commands
- Any natural language query!

Example session:
```
dataagent> load sales.csv
✓ Loaded source: sales.csv

dataagent> Show me the top 5 products
┏━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┓
┃ Product   ┃ Revenue ┃ Units    ┃
┡━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━┩
│ Widget A  │ $45,230 │ 523      │
│ Gadget B  │ $38,195 │ 412      │
│ Tool C    │ $31,847 │ 387      │
│ Device D  │ $28,934 │ 298      │
│ Item E    │ $25,123 │ 276      │
└───────────┴─────────┴──────────┘

dataagent> What's the average order value?
Average order value: $87.43

dataagent> exit
Goodbye!
```

## Advanced Examples

### Complex Analysis

```bash
# Multi-step analysis
dataagent analyze "
  Find customers who ordered in Q1 but not Q2,
  calculate their average order value,
  and identify the products they preferred
" -s orders.csv

# Statistical analysis
dataagent analyze "
  Perform regression analysis on sales vs marketing spend
  and predict next quarter's revenue
" -s business_data.csv
```

### Data Transformation

```bash
# Clean and transform data
dataagent analyze "
  Remove duplicates,
  fill missing values with median,
  and standardize the date formats
" -s messy_data.csv -o clean_data.csv
```

### Report Generation

```bash
# Generate comprehensive report
dataagent analyze "
  Create executive summary with:
  - Key metrics and KPIs
  - Trend analysis with charts
  - Actionable recommendations
" -s quarterly_data.csv -f json -o report.json
```

## Configuration

### Set Configuration Values

```bash
# Set default data source
dataagent config set default_source postgresql://localhost/main

# Set output preferences
dataagent config set default_format table
dataagent config set chart_style seaborn

# Set resource limits
dataagent config set max_rows 10000
dataagent config set timeout 30
```

### View Configuration

```bash
# List all settings
dataagent config list

# Get specific setting
dataagent config get default_source
```

## Security Features

DataAgent automatically protects your data:

- **PII Detection**: Automatically masks personal information
- **Credential Redaction**: Never logs passwords or API keys
- **SQL Injection Prevention**: Validates all database queries
- **Sandboxed Execution**: Runs analyses in isolated environment

## Tips & Tricks

### 1. Use Aliases
```bash
# Short alias 'da' is also available
da analyze "Quick analysis" -s data.csv
```

### 2. Environment Variables
```bash
export DATAAGENT_DEFAULT_SOURCE=postgresql://localhost/main
dataagent analyze "Show recent orders"  # Uses default source
```

### 3. Pipe Data
```bash
cat data.json | dataagent analyze "Find patterns"
```

### 4. Batch Processing
```bash
# Process multiple files
for file in *.csv; do
  dataagent analyze "Summarize" -s "$file" -o "${file%.csv}_summary.json"
done
```

### 5. Integration with Other Tools
```bash
# Combine with jq for JSON processing
dataagent analyze "Extract metrics" -s data.csv -f json | jq '.metrics'

# Use with grep for filtering
dataagent analyze "List all transactions" -s db.sqlite -f csv | grep "2024"
```

## Troubleshooting

### Authentication Issues

```bash
# Token expired
dataagent auth status  # Check expiry
dataagent auth login   # Re-authenticate

# Clear cached credentials
rm -rf ~/.dataagent/tokens.json
dataagent auth login
```

### Performance Optimization

```bash
# Limit data processing
dataagent analyze "Analysis" -s huge_file.csv --limit 1000

# Increase timeout for complex queries
dataagent config set timeout 120
```

### Debug Mode

```bash
# Enable verbose output
export DATAAGENT_DEBUG=1
dataagent analyze "Debug query" -s data.csv

# Check logs
tail -f ~/.dataagent/logs/dataagent.log
```

## Examples Repository

Find more examples at: https://github.com/jmanhype/dataagent-examples

- Sales Analysis
- Customer Segmentation
- Financial Reports
- Log Analysis
- Scientific Data Processing
- Real-time Monitoring

## Support

- **Documentation**: https://docs.dataagent.ai
- **Issues**: https://github.com/jmanhype/multi-agent-system/issues
- **Discord**: https://discord.gg/dataagent
- **Email**: support@dataagent.ai

## License

MIT License - Use freely in your projects!

---

**Built with ❤️ by the DataAgent Team**