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
        
        # Safely extract text content from possibly mixed content blocks
        content_blocks = getattr(response, "content", []) or []
        text_parts = []
        for block in content_blocks:
            text = getattr(block, "text", None)
            if text is None and isinstance(block, dict):
                text = block.get("text")
            if isinstance(text, str):
                text_parts.append(text)
        response_text = "\n".join(text_parts).strip()
        
        try:
            parsed_json = self._extract_json_object(response_text)
            parsed_json = self._validate_parsed_intent(parsed_json)
            
            operations = []
            for op in parsed_json["operations"]:
                if not isinstance(op, dict):
                    raise ValueError("Each operation must be an object")
                if "id" not in op or "description" not in op:
                    raise KeyError("operation missing `id` or `description`")
                deps = op.get("dependencies", [])
                if deps is None:
                    deps = []
                if not isinstance(deps, list):
                    raise ValueError("`dependencies` must be a list")
                operations.append(
                    Operation(
                        id=str(op["id"]),
                        description=str(op["description"]),
                        dependencies=[str(d) for d in deps],
                    )
                )
            
            return ParsedIntent(
                objective=str(parsed_json["objective"]),
                data_requirements=list(parsed_json["data_requirements"]),
                operations=operations,
                deliverables=list(parsed_json["deliverables"]),
                constraints=list(parsed_json.get("constraints", [])),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
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
    
    def _extract_json_object(self, text: str) -> Dict[str, Any]:
        """Extract JSON object from LLM response, handling markdown fences."""
        stripped = text.strip()
        
        # Strip markdown code fences if present
        if stripped.startswith("```"):
            first_newline = stripped.find("\n")
            if first_newline != -1:
                stripped = stripped[first_newline + 1 :]
            if stripped.endswith("```"):
                stripped = stripped[:-3].strip()
        
        # Attempt direct parse
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass
        
        # Fallback: find first top-level JSON object
        start = stripped.find("{")
        if start == -1:
            raise ValueError("No JSON object start found in LLM response.")
        
        depth = 0
        for i, ch in enumerate(stripped[start:], start=start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = stripped[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break
        
        raise ValueError("Failed to extract valid JSON object from LLM response.")
    
    def _validate_parsed_intent(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parsed intent structure and types."""
        required_keys = ["objective", "data_requirements", "operations", "deliverables"]
        for k in required_keys:
            if k not in data:
                raise ValueError(f"Missing required field '{k}' in parsed intent JSON.")
        
        if not isinstance(data["objective"], str):
            raise ValueError("Field 'objective' must be a string.")
        if not isinstance(data["data_requirements"], list):
            raise ValueError("Field 'data_requirements' must be a list.")
        if not isinstance(data["deliverables"], list):
            raise ValueError("Field 'deliverables' must be a list.")
        if not isinstance(data.get("constraints", []), list):
            raise ValueError("Field 'constraints' must be a list if provided.")
        
        ops = data["operations"]
        if not isinstance(ops, list) or not ops:
            raise ValueError("Field 'operations' must be a non-empty list.")
        
        for idx, op in enumerate(ops):
            if not isinstance(op, dict):
                raise ValueError(f"Operation at index {idx} must be an object.")
            if not isinstance(op.get("id"), str) or not isinstance(op.get("description"), str):
                raise ValueError(f"Operation {op} must have string 'id' and 'description'.")
            deps = op.get("dependencies", [])
            if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps):
                raise ValueError(f"Operation {op.get('id')} has invalid 'dependencies'; must be list[str].")
        
        return data
    
    def _build_user_message(self, intent: str) -> str:
        """Build user message for LLM."""
        return f"Parse this analysis request:\n\n{intent}"