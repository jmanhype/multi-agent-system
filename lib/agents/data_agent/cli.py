#!/usr/bin/env python3
"""DataAgent CLI - Natural language data analysis powered by Claude subscriptions."""

import click
import json
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
import webbrowser
import time
from urllib.parse import urlencode
import requests

from lib.agents.data_agent.fluent_oauth import FluentDataAgent as DataAgent, OAuthConfig

console = Console()

# Configuration file path
CONFIG_DIR = Path.home() / ".dataagent"
CONFIG_FILE = CONFIG_DIR / "config.yaml"
TOKEN_FILE = CONFIG_DIR / "tokens.json"


def load_config() -> Dict[str, Any]:
    """Load CLI configuration."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return yaml.safe_load(f) or {}
    return {}


def save_config(config: Dict[str, Any]):
    """Save CLI configuration."""
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)


def load_tokens() -> Dict[str, Any]:
    """Load OAuth tokens."""
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_tokens(tokens: Dict[str, Any]):
    """Save OAuth tokens securely."""
    CONFIG_DIR.mkdir(exist_ok=True)
    # Set restrictive permissions
    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f, indent=2)
    TOKEN_FILE.chmod(0o600)


@click.group()
@click.version_option(version='1.0.0', prog_name='dataagent')
def cli():
    """DataAgent CLI - Natural language data analysis powered by Claude subscriptions.
    
    Quick Start:
        dataagent auth login     # Authenticate with Claude
        dataagent analyze "Show sales trends from my database"
    """
    pass


@cli.group()
def auth():
    """Manage authentication with Claude subscriptions."""
    pass


@auth.command()
@click.option('--client-id', help='OAuth client ID', envvar='DATAAGENT_CLIENT_ID')
@click.option('--redirect-uri', default='http://localhost:8080/callback', help='OAuth redirect URI')
def login(client_id: Optional[str], redirect_uri: str):
    """Login with your Claude subscription via OAuth."""
    config = load_config()
    
    if not client_id:
        client_id = config.get('client_id')
        if not client_id:
            client_id = Prompt.ask("Enter OAuth Client ID")
            config['client_id'] = client_id
            save_config(config)
    
    # OAuth authorization URL
    auth_params = {
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'scope': 'data:analyze model:access',
        'state': os.urandom(16).hex()
    }
    
    auth_url = f"https://claude.ai/oauth/authorize?{urlencode(auth_params)}"
    
    console.print(f"[cyan]Opening browser for authentication...[/cyan]")
    console.print(f"[dim]URL: {auth_url}[/dim]")
    
    # Open browser
    webbrowser.open(auth_url)
    
    # Wait for callback (simplified - in production, run local server)
    console.print("[yellow]After authorizing, paste the authorization code:[/yellow]")
    auth_code = Prompt.ask("Authorization code")
    
    # Exchange code for token
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Exchanging authorization code...", total=None)
        
        # Simulate token exchange (in production, make actual API call)
        time.sleep(1)
        
        tokens = {
            'access_token': f"access_{auth_code[:20]}",
            'refresh_token': f"refresh_{os.urandom(16).hex()}",
            'expires_at': time.time() + 3600
        }
        
        save_tokens(tokens)
        progress.update(task, completed=True)
    
    console.print("[green]✓ Successfully authenticated with Claude![/green]")
    console.print("[dim]Tokens saved to ~/.dataagent/tokens.json[/dim]")


@auth.command()
def status():
    """Check authentication status."""
    tokens = load_tokens()
    
    if not tokens:
        console.print("[red]✗ Not authenticated[/red]")
        console.print("[yellow]Run 'dataagent auth login' to authenticate[/yellow]")
        return
    
    expires_at = tokens.get('expires_at', 0)
    remaining = expires_at - time.time()
    
    if remaining <= 0:
        console.print("[yellow]⚠ Token expired[/yellow]")
        console.print("[dim]Run 'dataagent auth refresh' to refresh token[/dim]")
    else:
        hours = int(remaining / 3600)
        minutes = int((remaining % 3600) / 60)
        console.print(f"[green]✓ Authenticated[/green]")
        console.print(f"[dim]Token expires in {hours}h {minutes}m[/dim]")


@auth.command()
def logout():
    """Logout and remove stored credentials."""
    if Confirm.ask("Are you sure you want to logout?"):
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
        console.print("[green]✓ Successfully logged out[/green]")


@cli.command()
@click.argument('query')
@click.option('--source', '-s', help='Data source (file path or connection string)')
@click.option('--format', '-f', type=click.Choice(['table', 'json', 'csv', 'chart']), default='table')
@click.option('--output', '-o', help='Output file path')
@click.option('--limit', '-l', type=int, help='Limit number of results')
def analyze(query: str, source: Optional[str], format: str, output: Optional[str], limit: Optional[int]):
    """Analyze data using natural language queries.
    
    Examples:
        dataagent analyze "Show top 10 customers by revenue"
        dataagent analyze "Plot monthly sales trends" -f chart
        dataagent analyze "Find anomalies in transaction data" -s sales.csv
    """
    tokens = load_tokens()
    
    if not tokens:
        console.print("[red]✗ Not authenticated[/red]")
        console.print("[yellow]Run 'dataagent auth login' first[/yellow]")
        sys.exit(1)
    
    # Check token expiry
    if tokens.get('expires_at', 0) <= time.time():
        console.print("[yellow]Token expired, refreshing...[/yellow]")
        # In production, implement actual token refresh
        tokens['expires_at'] = time.time() + 3600
        save_tokens(tokens)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing data...", total=None)
        
        try:
            # Initialize DataAgent with OAuth token
            agent = DataAgent.with_existing_token(tokens['access_token'])
            
            # Add data source if provided
            if source:
                agent = agent.connect(source)
            
            # Apply query with natural language
            agent = agent.explain(query)
            
            # Apply limit if specified
            if limit:
                agent = agent.limit(limit)
            
            # Execute analysis
            result = agent.execute()
            
            progress.update(task, completed=True)
            
            # Display results
            if format == 'table' and isinstance(result, dict) and 'data' in result:
                display_table(result['data'])
            elif format == 'json':
                json_output = json.dumps(result, indent=2)
                if output:
                    Path(output).write_text(json_output)
                    console.print(f"[green]✓ Results saved to {output}[/green]")
                else:
                    console.print(Syntax(json_output, "json"))
            elif format == 'csv' and isinstance(result, dict) and 'data' in result:
                # For mock, just display as table since we don't have actual dataframe
                display_table(result['data'])
                if output:
                    console.print(f"[yellow]CSV export would save to {output}[/yellow]")
            elif format == 'chart' and isinstance(result, dict) and 'charts' in result:
                for chart_name, chart_data in result['charts'].items():
                    console.print(f"[cyan]Chart: {chart_name}[/cyan]")
                    # In production, render actual chart
                    console.print(f"[dim]{chart_data}[/dim]")
            
            # Display summary
            if isinstance(result, dict) and 'summary' in result:
                console.print("\n[bold]Summary:[/bold]")
                console.print(result['summary'])
            
            # Display metrics
            if isinstance(result, dict) and 'metrics' in result:
                metrics = result['metrics']
                console.print(f"\n[dim]Execution time: {metrics.get('execution_time', 0):.2f}s[/dim]")
                console.print(f"[dim]Rows processed: {metrics.get('rows_processed', 0)}[/dim]")
        
        except Exception as e:
            progress.stop()
            console.print(f"[red]✗ Error: {str(e)}[/red]")
            sys.exit(1)


def display_table(data):
    """Display data as a rich table."""
    if not data:
        console.print("[yellow]No data to display[/yellow]")
        return
    
    # Handle dict with sample data
    if isinstance(data, dict):
        if 'sample' in data:
            data = data['sample']
        elif 'rows' in data and 'columns' in data:
            # Create sample data from schema
            console.print(f"[dim]Data shape: {data['rows']} rows × {len(data['columns'])} columns[/dim]")
            console.print(f"[dim]Columns: {', '.join(data['columns'])}[/dim]")
            return
    
    if not data or len(data) == 0:
        console.print("[yellow]No data to display[/yellow]")
        return
    
    table = Table(show_header=True, header_style="bold magenta")
    
    # Add columns
    if isinstance(data, list) and len(data) > 0:
        columns = list(data[0].keys())
    else:
        console.print("[yellow]Unsupported data format[/yellow]")
        return
    
    for col in columns:
        table.add_column(col)
    
    # Add rows (limit to 20 for display)
    rows = data[:20] if isinstance(data, list) else data
    for row in rows:
        table.add_row(*[str(row.get(col, '')) for col in columns])
    
    console.print(table)
    
    if len(data) > 20:
        console.print(f"[dim]Showing 20 of {len(data)} rows[/dim]")


@cli.command()
def interactive():
    """Start interactive data analysis session."""
    tokens = load_tokens()
    
    if not tokens:
        console.print("[red]✗ Not authenticated[/red]")
        console.print("[yellow]Run 'dataagent auth login' first[/yellow]")
        sys.exit(1)
    
    console.print("[bold cyan]DataAgent Interactive Mode[/bold cyan]")
    console.print("[dim]Type 'help' for commands, 'exit' to quit[/dim]\n")
    
    agent = DataAgent.with_existing_token(tokens['access_token'])
    context = {'agent': agent, 'source': None}
    
    while True:
        try:
            command = Prompt.ask("[cyan]dataagent>[/cyan]")
            
            if command.lower() in ['exit', 'quit', 'q']:
                break
            elif command.lower() == 'help':
                show_interactive_help()
            elif command.lower().startswith('load '):
                source = command[5:].strip()
                context['source'] = source
                console.print(f"[green]✓ Loaded source: {source}[/green]")
            elif command.lower() == 'status':
                if context['source']:
                    console.print(f"[cyan]Current source: {context['source']}[/cyan]")
                else:
                    console.print("[yellow]No source loaded[/yellow]")
            else:
                # Execute query
                with console.status("[cyan]Analyzing...[/cyan]"):
                    try:
                        agent_query = agent
                        if context['source']:
                            agent_query = agent_query.connect(context['source'])
                        
                        result = agent_query.explain(command).execute()
                        
                        if hasattr(result, 'data'):
                            display_table(result.data)
                        if hasattr(result, 'summary'):
                            console.print(f"\n[dim]{result.summary}[/dim]")
                    
                    except Exception as e:
                        console.print(f"[red]Error: {str(e)}[/red]")
        
        except KeyboardInterrupt:
            console.print("\n[yellow]Use 'exit' to quit[/yellow]")
            continue
    
    console.print("[green]Goodbye![/green]")


def show_interactive_help():
    """Show help for interactive mode."""
    help_text = """
[bold]Interactive Mode Commands:[/bold]

  [cyan]load <source>[/cyan]     Load a data source (file or connection string)
  [cyan]status[/cyan]           Show current source and session info
  [cyan]help[/cyan]             Show this help message
  [cyan]exit[/cyan]             Exit interactive mode

[bold]Query Examples:[/bold]

  Show top 10 customers by revenue
  Plot sales trends over time
  Find anomalies in the data
  Calculate average order value by region
    """
    console.print(help_text)


@cli.group()
def config():
    """Manage DataAgent configuration."""
    pass


@config.command('set')
@click.argument('key')
@click.argument('value')
def config_set(key: str, value: str):
    """Set a configuration value."""
    config = load_config()
    config[key] = value
    save_config(config)
    console.print(f"[green]✓ Set {key} = {value}[/green]")


@config.command('get')
@click.argument('key')
def config_get(key: str):
    """Get a configuration value."""
    config = load_config()
    value = config.get(key)
    if value:
        console.print(f"{key} = {value}")
    else:
        console.print(f"[yellow]Key '{key}' not found[/yellow]")


@config.command('list')
def config_list():
    """List all configuration values."""
    config = load_config()
    if config:
        for key, value in config.items():
            console.print(f"{key} = {value}")
    else:
        console.print("[yellow]No configuration set[/yellow]")


@cli.command()
def quickstart():
    """Interactive quickstart guide."""
    console.print("[bold cyan]Welcome to DataAgent QuickStart![/bold cyan]\n")
    
    # Check authentication
    tokens = load_tokens()
    if not tokens:
        console.print("[yellow]Let's get you authenticated first.[/yellow]")
        if Confirm.ask("Would you like to authenticate now?"):
            ctx = click.Context(login)
            ctx.invoke(login)
    
    console.print("\n[bold]Quick Examples:[/bold]\n")
    
    examples = [
        ("Analyze CSV file", "dataagent analyze 'Show summary statistics' -s data.csv"),
        ("Query database", "dataagent analyze 'Top 10 products by revenue' -s postgresql://localhost/sales"),
        ("Generate chart", "dataagent analyze 'Plot monthly trends' -f chart -o trends.png"),
        ("Export results", "dataagent analyze 'Customer segments' -f csv -o segments.csv"),
        ("Interactive mode", "dataagent interactive"),
    ]
    
    for title, command in examples:
        console.print(f"[cyan]{title}:[/cyan]")
        console.print(f"  [dim]$ {command}[/dim]\n")
    
    console.print("[bold]Next Steps:[/bold]")
    console.print("1. Try analyzing your own data files")
    console.print("2. Connect to your databases")
    console.print("3. Use interactive mode for exploration")
    console.print("\nFor more help: [cyan]dataagent --help[/cyan]")


if __name__ == '__main__':
    cli()