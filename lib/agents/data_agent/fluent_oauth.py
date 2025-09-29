"""
Fluent API for DataAgent with OAuth authentication using Claude subscriptions.

This implementation allows third-party agents to leverage users' existing
Claude Code subscriptions instead of requiring separate API keys.
"""
import os
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import uuid
import json
from urllib.parse import urlencode
import webbrowser


class AuthProvider(Enum):
    """Supported authentication providers."""
    CLAUDE_CODE = "claude_code"
    OPENCODE = "opencode"
    MCP_SERVER = "mcp_server"


@dataclass
class OAuthConfig:
    """OAuth configuration for Claude subscription authentication."""
    client_id: str
    redirect_uri: str = "http://localhost:8080/callback"
    scope: str = "read:subscription execute:claude"
    auth_endpoint: str = "https://auth.anthropic.com/oauth/authorize"
    token_endpoint: str = "https://auth.anthropic.com/oauth/token"
    provider: AuthProvider = AuthProvider.CLAUDE_CODE


class ClaudeOAuthSession:
    """Manages OAuth session with Claude subscription."""
    
    def __init__(self, config: OAuthConfig):
        self.config = config
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.subscription_tier: Optional[str] = None
        
    def authenticate(self) -> bool:
        """
        Initiate OAuth flow to authenticate with user's Claude subscription.
        Returns True if authentication successful.
        """
        # Check for cached token first
        cached_token = self._load_cached_token()
        if cached_token and self._validate_token(cached_token):
            self.access_token = cached_token
            return True
            
        # Initiate OAuth flow
        state = str(uuid.uuid4())
        auth_params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": self.config.scope,
            "state": state,
            "response_type": "code"
        }
        
        auth_url = f"{self.config.auth_endpoint}?{urlencode(auth_params)}"
        
        print(f"🔐 Authentication required. Opening browser...")
        print(f"   If browser doesn't open, visit: {auth_url}")
        
        # In production, this would open browser and handle callback
        # For now, we'll simulate success
        webbrowser.open(auth_url)
        
        # Simulate receiving auth code (in production, run local server)
        auth_code = self._wait_for_callback(state)
        
        if auth_code:
            self.access_token = self._exchange_code_for_token(auth_code)
            self._cache_token(self.access_token)
            return True
            
        return False
    
    def _load_cached_token(self) -> Optional[str]:
        """Load cached OAuth token from secure storage."""
        token_file = os.path.expanduser("~/.claude_oauth_token")
        if os.path.exists(token_file):
            try:
                with open(token_file, 'r') as f:
                    data = json.load(f)
                    return data.get("access_token")
            except:
                pass
        return None
    
    def _cache_token(self, token: str):
        """Cache OAuth token securely."""
        token_file = os.path.expanduser("~/.claude_oauth_token")
        os.makedirs(os.path.dirname(token_file), exist_ok=True)
        with open(token_file, 'w') as f:
            json.dump({"access_token": token}, f)
        os.chmod(token_file, 0o600)  # Secure file permissions
    
    def _validate_token(self, token: str) -> bool:
        """Validate that token is still active."""
        # In production, make API call to validate
        # For now, assume valid if exists
        return bool(token)
    
    def _wait_for_callback(self, state: str) -> Optional[str]:
        """Wait for OAuth callback with auth code."""
        # In production, run local HTTP server to receive callback
        # For demo, we'll simulate success
        print("⏳ Waiting for authentication...")
        # Simulated auth code
        return "mock_auth_code_" + state[:8]
    
    def _exchange_code_for_token(self, code: str) -> str:
        """Exchange authorization code for access token."""
        # In production, POST to token endpoint
        # For demo, return mock token
        return f"claude_access_token_{uuid.uuid4().hex[:16]}"
    
    def get_subscription_tier(self) -> str:
        """Get user's Claude subscription tier for rate limiting."""
        if not self.subscription_tier and self.access_token:
            # In production, call API to get subscription details
            self.subscription_tier = "pro"  # Mock tier
        return self.subscription_tier or "free"


class FluentDataAgent:
    """
    Fluent API for data analysis using Claude subscriptions.
    
    Example:
        agent = FluentDataAgent.with_claude_auth(client_id="your_app_id")
        
        result = (agent
            .connect("postgresql://localhost/sales")
            .query("SELECT * FROM transactions WHERE date > '2024-01-01'")
            .filter(lambda df: df['amount'] > 100)
            .aggregate(['category'], 'sum', 'amount')
            .visualize('bar')
            .explain("What are the top performing categories?")
            .execute())
    """
    
    def __init__(self, oauth_session: Optional[ClaudeOAuthSession] = None):
        self.oauth_session = oauth_session
        self._pipeline = []
        self._data_sources = []
        self._transformations = []
        self._visualizations = []
        self._explanations = []
        self._constraints = {}
        
    @classmethod
    def with_claude_auth(cls, client_id: str, provider: AuthProvider = AuthProvider.CLAUDE_CODE) -> 'FluentDataAgent':
        """
        Create agent with Claude OAuth authentication.
        
        Args:
            client_id: Your application's OAuth client ID
            provider: Authentication provider (defaults to CLAUDE_CODE)
        """
        config = OAuthConfig(client_id=client_id, provider=provider)
        session = ClaudeOAuthSession(config)
        
        if not session.authenticate():
            raise RuntimeError("Failed to authenticate with Claude subscription")
            
        print(f"✅ Authenticated successfully!")
        print(f"   Subscription tier: {session.get_subscription_tier()}")
        
        return cls(oauth_session=session)
    
    @classmethod
    def with_existing_token(cls, token: str) -> 'FluentDataAgent':
        """
        Create agent with existing OAuth token.
        
        Args:
            token: Existing OAuth access token
        """
        session = ClaudeOAuthSession(OAuthConfig(client_id="reused"))
        session.access_token = token
        return cls(oauth_session=session)
    
    def connect(self, source: Union[str, Dict[str, Any]]) -> 'FluentDataAgent':
        """Connect to a data source."""
        if isinstance(source, str):
            # Parse connection string or file path
            if source.startswith(('postgresql://', 'mysql://', 'sqlite://')):
                self._data_sources.append({"type": "sql", "connection_string": source})
            elif source.endswith(('.csv', '.parquet', '.json')):
                self._data_sources.append({"type": "file", "path": source})
            else:
                self._data_sources.append({"type": "unknown", "source": source})
        else:
            self._data_sources.append(source)
        return self
    
    def query(self, sql: str) -> 'FluentDataAgent':
        """Add SQL query to pipeline."""
        self._pipeline.append({"action": "query", "sql": sql})
        return self
    
    def filter(self, condition: Union[str, callable]) -> 'FluentDataAgent':
        """Filter data based on condition."""
        if callable(condition):
            self._pipeline.append({"action": "filter", "function": condition})
        else:
            self._pipeline.append({"action": "filter", "expression": condition})
        return self
    
    def aggregate(self, group_by: List[str], agg_func: str, column: str) -> 'FluentDataAgent':
        """Aggregate data."""
        self._pipeline.append({
            "action": "aggregate",
            "group_by": group_by,
            "function": agg_func,
            "column": column
        })
        return self
    
    def transform(self, transformation: Union[str, callable]) -> 'FluentDataAgent':
        """Apply transformation to data."""
        if callable(transformation):
            self._transformations.append({"type": "function", "func": transformation})
        else:
            self._transformations.append({"type": "expression", "expr": transformation})
        return self
    
    def visualize(self, chart_type: str, **kwargs) -> 'FluentDataAgent':
        """Add visualization to output."""
        self._visualizations.append({
            "type": chart_type,
            "options": kwargs
        })
        return self
    
    def explain(self, question: str) -> 'FluentDataAgent':
        """Add natural language explanation request."""
        self._explanations.append(question)
        return self
    
    def limit(self, rows: int) -> 'FluentDataAgent':
        """Limit number of rows returned."""
        self._constraints["row_limit"] = rows
        return self
    
    def timeout(self, seconds: int) -> 'FluentDataAgent':
        """Set execution timeout."""
        self._constraints["timeout_seconds"] = seconds
        return self
    
    def cache(self, duration: int = 3600) -> 'FluentDataAgent':
        """Enable result caching."""
        self._constraints["cache_duration"] = duration
        return self
    
    def safe_mode(self) -> 'FluentDataAgent':
        """Enable safe mode (no destructive operations)."""
        self._constraints["safe_mode"] = True
        return self
    
    def execute(self) -> Dict[str, Any]:
        """
        Execute the analysis pipeline using Claude subscription.
        
        Returns:
            Dict containing results, visualizations, and explanations
        """
        if not self.oauth_session or not self.oauth_session.access_token:
            raise RuntimeError("Not authenticated. Use with_claude_auth() first.")
        
        # Build analysis request
        request_id = str(uuid.uuid4())
        
        # Construct natural language intent from pipeline
        intent = self._build_intent()
        
        # Prepare deliverables
        deliverables = []
        if self._pipeline:
            deliverables.append("data")
        if self._visualizations:
            deliverables.append("charts")
        if self._explanations:
            deliverables.append("insights")
        
        # Execute via Claude API using OAuth token
        response = self._execute_with_claude(
            request_id=request_id,
            intent=intent,
            deliverables=deliverables
        )
        
        return response
    
    def _build_intent(self) -> str:
        """Build natural language intent from pipeline."""
        parts = []
        
        if self._data_sources:
            parts.append(f"Analyze data from {len(self._data_sources)} source(s)")
        
        for step in self._pipeline:
            if step["action"] == "query":
                parts.append(f"Run SQL: {step['sql'][:50]}...")
            elif step["action"] == "filter":
                parts.append("Apply filtering")
            elif step["action"] == "aggregate":
                parts.append(f"Group by {step['group_by']} and {step['function']}")
        
        if self._visualizations:
            chart_types = [v["type"] for v in self._visualizations]
            parts.append(f"Create {', '.join(chart_types)} visualizations")
        
        if self._explanations:
            parts.append(f"Answer: {self._explanations[0]}")
        
        return "; ".join(parts)
    
    def _execute_with_claude(self, request_id: str, intent: str, deliverables: List[str]) -> Dict[str, Any]:
        """
        Execute analysis using Claude API with OAuth authentication.
        
        This is where the magic happens - instead of requiring API keys,
        we use the user's existing Claude subscription via OAuth.
        """
        headers = {
            "Authorization": f"Bearer {self.oauth_session.access_token}",
            "X-Subscription-Tier": self.oauth_session.get_subscription_tier()
        }
        
        # In production, this would make actual API call to Claude
        # For demo, we'll return mock response
        print(f"\n🚀 Executing analysis via Claude subscription...")
        print(f"   Request ID: {request_id}")
        print(f"   Intent: {intent}")
        print(f"   Using subscription tier: {self.oauth_session.get_subscription_tier()}")
        
        # Simulate execution
        result = {
            "request_id": request_id,
            "status": "success",
            "data": {
                "rows": 42,
                "columns": ["category", "total_amount", "count"],
                "sample": [
                    {"category": "Electronics", "total_amount": 125000, "count": 89},
                    {"category": "Clothing", "total_amount": 87500, "count": 156},
                ]
            },
            "insights": "Electronics shows highest revenue despite lower transaction count, suggesting higher average order value.",
            "execution_time": 1.23,
            "credits_used": 0  # No credits needed - using subscription!
        }
        
        if self._visualizations:
            result["charts"] = [
                {"type": v["type"], "url": f"https://charts.claude.ai/{request_id}/{i}.png"}
                for i, v in enumerate(self._visualizations)
            ]
        
        return result
    
    def dry_run(self) -> Dict[str, Any]:
        """Preview what would be executed without running."""
        return {
            "data_sources": self._data_sources,
            "pipeline": self._pipeline,
            "transformations": self._transformations,
            "visualizations": self._visualizations,
            "explanations": self._explanations,
            "constraints": self._constraints,
            "intent": self._build_intent()
        }


# Convenience function for quick start
def analyze_with_claude(client_id: str) -> FluentDataAgent:
    """
    Quick start function to create authenticated agent.
    
    Example:
        from lib.agents.data_agent.fluent_oauth import analyze_with_claude
        
        result = (analyze_with_claude("my_app_id")
            .connect("sales.csv")
            .filter("amount > 100")
            .visualize("pie", field="category")
            .execute())
    """
    return FluentDataAgent.with_claude_auth(client_id)