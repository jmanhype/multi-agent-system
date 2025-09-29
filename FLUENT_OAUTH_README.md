# Fluent DataAgent with Claude OAuth Authentication

## Overview

This implementation provides a fluent API for data analysis that leverages users' existing Claude Code subscriptions through OAuth authentication, eliminating the need for separate API keys.

## Key Innovation: Zero-Cost Integration

Traditional approach:
- Developers need their own API keys
- Users pay twice (Claude subscription + API costs)
- Complex key management

Our approach:
- Uses existing Claude subscriptions via OAuth
- No additional costs for users
- Simple authentication flow
- Automatic rate limiting based on subscription tier

## Quick Start

```python
from lib.agents.data_agent.fluent_oauth import analyze_with_claude

# One-line authentication and analysis
result = (analyze_with_claude("your_app_id")
    .connect("sales.csv")
    .filter("revenue > 1000")
    .visualize("bar")
    .execute())
```

## Installation

```bash
# No API keys to configure!
pip install fluent-data-agent
```

## Authentication Flow

1. **First Use**: User authenticates with their Claude account
2. **Token Caching**: Credentials cached securely for future use
3. **Automatic Refresh**: Tokens refreshed automatically when needed

## Usage Examples

### Basic Analysis

```python
from lib.agents.data_agent.fluent_oauth import FluentDataAgent

# Authenticate once
agent = FluentDataAgent.with_claude_auth(client_id="your_app_id")

# Chain operations fluently
result = (agent
    .connect("data.csv")
    .filter("amount > 100")
    .aggregate(['category'], 'sum', 'amount')
    .visualize('pie')
    .execute())
```

### Complex Multi-Source Pipeline

```python
result = (agent
    .connect("postgresql://localhost/sales")
    .connect("customers.parquet")
    .query("""
        SELECT c.*, s.* 
        FROM sales s 
        JOIN customers c ON s.customer_id = c.id
    """)
    .filter(lambda df: df['revenue'] > 10000)
    .visualize('heatmap', x='segment', y='category')
    .explain("What patterns emerge in high-value transactions?")
    .execute())
```

### With Safety Constraints

```python
result = (agent
    .connect("sensitive_data.csv")
    .safe_mode()  # No destructive operations
    .limit(1000)  # Row limit
    .timeout(30)  # 30 second timeout
    .cache(3600)  # Cache for 1 hour
    .execute())
```

## API Reference

### Authentication Methods

- `FluentDataAgent.with_claude_auth(client_id)` - OAuth authentication
- `FluentDataAgent.with_existing_token(token)` - Use existing token

### Data Operations

- `.connect(source)` - Connect to data source (SQL, CSV, Parquet, JSON)
- `.query(sql)` - Execute SQL query
- `.filter(condition)` - Filter rows
- `.aggregate(group_by, func, column)` - Group and aggregate
- `.transform(func)` - Apply transformation

### Visualization & Insights

- `.visualize(type, **options)` - Create charts (bar, line, pie, heatmap, scatter)
- `.explain(question)` - Get natural language insights

### Constraints & Safety

- `.limit(rows)` - Limit output rows
- `.timeout(seconds)` - Set execution timeout
- `.cache(duration)` - Enable result caching
- `.safe_mode()` - Prevent destructive operations

### Execution

- `.execute()` - Run the pipeline
- `.dry_run()` - Preview without executing

## Subscription Tiers

The API automatically adapts to the user's Claude subscription:

| Tier | Daily Requests | Max Rows | Features |
|------|---------------|----------|----------|
| Free | 10 | 1,000 | Basic charts |
| Pro | Unlimited | Unlimited | Advanced visualizations, priority processing |
| Enterprise | Unlimited | Unlimited | Custom models, dedicated resources |

## OAuth Configuration

### For App Developers

1. Register your app at https://console.anthropic.com/oauth
2. Obtain your `client_id`
3. Configure redirect URI (default: `http://localhost:8080/callback`)

### For End Users

Simply authenticate once when prompted. The token is cached securely for future use.

## Security

- OAuth tokens stored with 600 permissions
- Automatic token refresh
- Secure credential handling
- No API keys in code

## Business Model Benefits

### For Developers
- **Zero API costs** - Users bring their own subscriptions
- **No key management** - OAuth handles authentication
- **Automatic scaling** - Rate limits based on user's tier

### For Users
- **No double payment** - Use existing Claude subscription
- **Unified billing** - One subscription for everything
- **Better security** - No API keys to leak

### For Anthropic
- **Increased subscription value** - More reasons to subscribe
- **Ecosystem growth** - Third-party apps enhance platform
- **User retention** - Subscriptions become more valuable

## Demo

Run the comprehensive demo:

```bash
python demo_oauth_fluent.py
```

This demonstrates:
- OAuth authentication flow
- Basic and complex pipelines
- Token caching
- Error handling
- Subscription tier detection

## Comparison with Traditional Approaches

| Aspect | Traditional API | OAuth Subscription |
|--------|----------------|-------------------|
| Cost for users | Subscription + API fees | Subscription only |
| Cost for developers | API fees | Free |
| Authentication | API keys | OAuth flow |
| Key management | Manual | Automatic |
| Rate limiting | Fixed | Based on user tier |
| Security | Keys can leak | OAuth tokens |

## Future Enhancements

- [ ] WebSocket support for streaming results
- [ ] Collaborative analysis sessions
- [ ] Template marketplace
- [ ] Visual pipeline builder
- [ ] Integration with Claude Code IDE

## Support

- Documentation: https://docs.claude-data-agent.ai
- Issues: https://github.com/your-org/fluent-data-agent/issues
- Discord: https://discord.gg/claude-data-agent

## License

MIT - Use freely in your applications!

---

*Built to make data analysis accessible without the API key hassle.*