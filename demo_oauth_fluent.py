#!/usr/bin/env python3
"""
Demo: Fluent DataAgent API with Claude OAuth Authentication

This demo shows how third-party agents can leverage users' existing
Claude Code subscriptions instead of requiring separate API keys.

Key Benefits:
1. No double payment - Users already pay for Claude
2. Zero API costs for developers
3. Simple authentication flow
4. Automatic rate limiting based on subscription tier
"""

from lib.agents.data_agent.fluent_oauth import FluentDataAgent, analyze_with_claude


def demo_basic_usage():
    """Basic usage with OAuth authentication."""
    print("=" * 60)
    print("Demo 1: Basic OAuth Authentication and Analysis")
    print("=" * 60)
    
    # Users authenticate once with their Claude account
    # No API keys needed!
    agent = FluentDataAgent.with_claude_auth(
        client_id="demo_data_agent_app"  # Your app's OAuth client ID
    )
    
    # Now use the fluent API with full Claude capabilities
    result = (agent
        .connect("sales_data.csv")
        .filter("revenue > 1000")
        .aggregate(['region'], 'sum', 'revenue')
        .visualize('bar')
        .execute())
    
    print(f"\n✅ Analysis complete!")
    print(f"   Request ID: {result['request_id']}")
    print(f"   Status: {result['status']}")
    print(f"   Rows processed: {result['data']['rows']}")
    print(f"   Execution time: {result['execution_time']}s")
    print(f"   Credits used: {result['credits_used']} (Free with subscription!)")


def demo_complex_pipeline():
    """Complex analysis pipeline using subscription."""
    print("\n" + "=" * 60)
    print("Demo 2: Complex Multi-Source Analysis")
    print("=" * 60)
    
    agent = FluentDataAgent.with_claude_auth(
        client_id="demo_data_agent_app"
    )
    
    result = (agent
        # Connect to multiple data sources
        .connect("postgresql://localhost/sales")
        .connect("customers.parquet")
        
        # SQL query
        .query("""
            SELECT c.segment, s.product_category, 
                   SUM(s.revenue) as total_revenue,
                   COUNT(DISTINCT s.transaction_id) as transactions
            FROM sales s
            JOIN customers c ON s.customer_id = c.id
            WHERE s.date >= '2024-01-01'
            GROUP BY c.segment, s.product_category
        """)
        
        # Additional transformations
        .filter(lambda df: df['total_revenue'] > 10000)
        .transform(lambda df: df.assign(avg_transaction=df['total_revenue']/df['transactions']))
        
        # Multiple visualizations
        .visualize('heatmap', x='segment', y='product_category', value='total_revenue')
        .visualize('scatter', x='transactions', y='avg_transaction', color='segment')
        
        # Natural language insights
        .explain("What customer segments drive the most revenue per category?")
        .explain("Are there any unusual patterns in transaction sizes?")
        
        # Constraints
        .limit(1000)
        .timeout(30)
        .safe_mode()
        
        .execute())
    
    print(f"\n✅ Complex analysis complete!")
    print(f"   Data shape: {result['data']['rows']} rows")
    print(f"   Charts generated: {len(result.get('charts', []))}")
    print(f"   Insights: {result.get('insights', 'N/A')[:100]}...")


def demo_cached_token():
    """Use cached OAuth token for faster startup."""
    print("\n" + "=" * 60)
    print("Demo 3: Using Cached Authentication")
    print("=" * 60)
    
    # After first authentication, token is cached
    # Subsequent runs are instant!
    
    try:
        agent = FluentDataAgent.with_claude_auth(
            client_id="demo_data_agent_app"
        )
        print("✅ Authenticated using cached token!")
        
        # Quick analysis
        result = (agent
            .connect("transactions.json")
            .aggregate(['status'], 'count', '*')
            .visualize('pie')
            .execute())
        
        print(f"   Analysis completed in {result['execution_time']}s")
        
    except RuntimeError as e:
        print(f"❌ Authentication failed: {e}")


def demo_dry_run():
    """Preview analysis without execution."""
    print("\n" + "=" * 60)
    print("Demo 4: Dry Run (Preview Without Execution)")
    print("=" * 60)
    
    agent = FluentDataAgent.with_claude_auth(
        client_id="demo_data_agent_app"
    )
    
    # Build complex pipeline
    pipeline = (agent
        .connect("sales.csv")
        .query("SELECT * FROM sales WHERE region = 'West'")
        .filter("amount > 500")
        .aggregate(['product'], 'mean', 'amount')
        .visualize('bar')
        .explain("What products perform best in the West region?"))
    
    # Preview what would be executed
    preview = pipeline.dry_run()
    
    print("\n📋 Analysis Preview:")
    print(f"   Intent: {preview['intent']}")
    print(f"   Data sources: {len(preview['data_sources'])}")
    print(f"   Pipeline steps: {len(preview['pipeline'])}")
    print(f"   Visualizations: {preview['visualizations']}")
    print(f"   Questions: {preview['explanations']}")
    
    # User can review before executing
    print("\n   Would execute this? (In real app, prompt user)")


def demo_quick_start():
    """Ultra-simple one-liner analysis."""
    print("\n" + "=" * 60)
    print("Demo 5: Quick Start One-Liner")
    print("=" * 60)
    
    # Convenience function for quick analysis
    result = (analyze_with_claude("demo_data_agent_app")
        .connect("revenue.csv")
        .visualize("line", x="date", y="revenue")
        .execute())
    
    print(f"✅ Quick analysis done! Chart at: {result.get('charts', [{}])[0].get('url', 'N/A')}")


def demo_error_handling():
    """Demonstrate error handling and subscription tiers."""
    print("\n" + "=" * 60)
    print("Demo 6: Error Handling and Subscription Tiers")
    print("=" * 60)
    
    try:
        # Attempt without authentication
        agent = FluentDataAgent()
        result = agent.connect("data.csv").execute()
    except RuntimeError as e:
        print(f"❌ Expected error: {e}")
    
    # Authenticated agent
    agent = FluentDataAgent.with_claude_auth(
        client_id="demo_data_agent_app"
    )
    
    # Check subscription tier
    tier = agent.oauth_session.get_subscription_tier()
    print(f"\n📊 Subscription tier: {tier}")
    
    if tier == "free":
        print("   ⚠️  Free tier limitations:")
        print("      - 10 requests per day")
        print("      - Max 1000 rows per query")
        print("      - Basic visualizations only")
    elif tier == "pro":
        print("   ✨ Pro tier benefits:")
        print("      - Unlimited requests")
        print("      - Large dataset support")
        print("      - Advanced visualizations")
        print("      - Priority processing")


def main():
    """Run all demos."""
    print("""
╔════════════════════════════════════════════════════════════╗
║     Fluent DataAgent with Claude OAuth Authentication     ║
║                                                            ║
║  No API Keys Required - Uses Your Claude Subscription!    ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    demos = [
        ("Basic OAuth Usage", demo_basic_usage),
        ("Complex Pipeline", demo_complex_pipeline),
        ("Cached Authentication", demo_cached_token),
        ("Dry Run Preview", demo_dry_run),
        ("Quick Start", demo_quick_start),
        ("Error Handling", demo_error_handling),
    ]
    
    print("Available demos:")
    for i, (name, _) in enumerate(demos, 1):
        print(f"  {i}. {name}")
    
    print("\nRunning all demos...\n")
    
    for name, demo_func in demos:
        try:
            demo_func()
        except Exception as e:
            print(f"\n⚠️  Demo '{name}' encountered an error: {e}")
    
    print("""
╔════════════════════════════════════════════════════════════╗
║                    Demo Complete! 🎉                      ║
║                                                            ║
║  Key Advantages:                                          ║
║  • No separate API keys needed                            ║
║  • Leverages existing Claude subscriptions                ║
║  • Zero additional cost for users                         ║
║  • Simple OAuth flow                                      ║
║  • Automatic rate limiting by tier                        ║
╚════════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    main()