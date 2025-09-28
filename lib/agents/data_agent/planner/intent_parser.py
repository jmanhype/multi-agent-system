"""Intent parsing for DataAgent analysis requests.

Converts natural language intents into structured analysis plans using LLM.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import json
from anthropic import Anthropic


@dataclass
class Operation:
    """Single operation in analysis workflow.
    
    Attributes:
        id: Unique operation identifier
        description: Natural language description of operation
        dependencies: IDs of operations that must complete first
    """
    id: str
    description: str
    dependencies: List[str]


@dataclass
class ParsedIntent:
    """Structured representation of analysis intent.
    
    Attributes:
        objective: High-level goal (e.g., "identify top revenue-generating regions")
        data_requirements: Required data sources and columns
        operations: List of Operation objects with dependency information
        deliverables: Expected output artifacts (table, chart, summary)
        constraints: Policy constraints and guardrails to enforce
    """
    objective: str
    data_requirements: List[str]
    operations: List[Operation]
    deliverables: List[str]
    constraints: List[str]


class IntentParser:
    """Parse natural language intents into structured plans.
    
    Uses LLM to decompose user requests into actionable steps while
    maintaining safety guardrails and tool selection constraints.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.0,
    ):
        """Initialize intent parser.
        
        Args:
            api_key: Anthropic API key (reads from env if None)
            model: Claude model to use
            temperature: Sampling temperature (0.0 for deterministic)
        """
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.temperature = temperature
    
    def parse(
        self,
        intent: str,
        available_tools: List[str],
        schema_info: Optional[dict] = None,
    ) -> ParsedIntent:
        """Parse natural language intent into structured plan.
        
        Args:
            intent: User's natural language request
            available_tools: List of available tool names
            schema_info: Optional schema fingerprint and column metadata
        
        Returns:
            ParsedIntent with objective, operations, and deliverables
        
        Example:
            >>> parser = IntentParser()
            >>> intent = "Show me top 5 customers by revenue in Q4"
            >>> parsed = parser.parse(intent, ["sql_runner", "df_operations", "plotter"])
            >>> parsed.objective
            'Identify top 5 customers by Q4 revenue'
            >>> len(parsed.operations)
            5
        """
        system_prompt = self._build_system_prompt(available_tools, schema_info)
        user_message = self._build_user_message(intent)
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            temperature=self.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        
        response_text = response.content[0].text
        
        try:
            parsed_json = json.loads(response_text)
            operations = [
                Operation(
                    id=op["id"],
                    description=op["description"],
                    dependencies=op.get("dependencies", []),
                )
                for op in parsed_json["operations"]
            ]
            return ParsedIntent(
                objective=parsed_json["objective"],
                data_requirements=parsed_json["data_requirements"],
                operations=operations,
                deliverables=parsed_json["deliverables"],
                constraints=parsed_json.get("constraints", []),
            )
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"LLM returned invalid or incomplete JSON: {e}")
    
    def _build_system_prompt(
        self,
        available_tools: List[str],
        schema_info: Optional[dict],
    ) -> str:
        """Build system prompt for LLM intent parsing."""
        tool_list = "\n".join(f"- {tool}" for tool in available_tools)
        
        schema_section = ""
        if schema_info:
            schema_section = f"\n\nAvailable schema:\n{json.dumps(schema_info, indent=2)}"
        
        return f"""You are a data analysis planner. Parse user intents into structured analysis plans with dependency information.

Available tools:
{tool_list}{schema_section}

Output JSON with:
- objective: Clear goal statement
- data_requirements: List of required data sources/columns
- operations: List of operation objects with dependencies
  - Each operation has: id (unique identifier), description (what to do), dependencies (list of operation IDs that must complete first)
  - Operations with no prerequisites have empty dependencies list
  - Parallel operations can share the same dependencies
- deliverables: Expected outputs (table/chart/summary)
- constraints: Safety constraints to enforce

Example for sequential workflow:
{{
  "objective": "Identify top revenue-generating regions",
  "data_requirements": ["sales table", "region column", "revenue column"],
  "operations": [
    {{"id": "op1", "description": "Filter sales data for target period", "dependencies": []}},
    {{"id": "op2", "description": "Group by region", "dependencies": ["op1"]}},
    {{"id": "op3", "description": "Aggregate revenue sum", "dependencies": ["op2"]}},
    {{"id": "op4", "description": "Sort descending by revenue", "dependencies": ["op3"]}},
    {{"id": "op5", "description": "Take top N regions", "dependencies": ["op4"]}}
  ],
  "deliverables": ["ranked table", "bar chart"],
  "constraints": ["enforce row limit", "no PII access"]
}}

Example for parallel workflow:
{{
  "objective": "Compare sales and customer metrics",
  "data_requirements": ["sales table", "customers table"],
  "operations": [
    {{"id": "op1", "description": "Query sales data", "dependencies": []}},
    {{"id": "op2", "description": "Query customer data", "dependencies": []}},
    {{"id": "op3", "description": "Join sales with customers", "dependencies": ["op1", "op2"]}},
    {{"id": "op4", "description": "Calculate combined metrics", "dependencies": ["op3"]}}
  ],
  "deliverables": ["summary table"],
  "constraints": ["row_limit=10000"]
}}

Focus on logical operations, not tool implementation details. Identify which operations can run in parallel."""
    
    def _build_user_message(self, intent: str) -> str:
        """Build user message for LLM."""
        return f"Parse this analysis request:\n\n{intent}"