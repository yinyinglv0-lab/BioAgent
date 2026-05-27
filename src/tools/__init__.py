"""BioAgent tools - modular tool implementations for the Agent.

Provider-agnostic: tools are registered in a generic format and can be
converted to Claude ToolParam or OpenAI function-calling format on demand.
"""

import json
from typing import Any

# ============================================================
# Tool Registry
# ============================================================

TOOL_REGISTRY: dict[str, dict[str, Any]] = {}


def register(name: str, description: str, input_schema: dict[str, Any]):
    """Decorator-less registration of a tool."""
    def decorator(func):
        TOOL_REGISTRY[name] = {
            "name": name,
            "description": description,
            "input_schema": input_schema,
            "func": func,
        }
        return func
    return decorator


def get_tools_anthropic() -> list:
    """Return tools in Anthropic/Claude ToolParam format."""
    from anthropic.types import ToolParam
    tools = []
    for info in TOOL_REGISTRY.values():
        tools.append(ToolParam(
            name=info["name"],
            description=info["description"],
            input_schema=info["input_schema"],
        ))
    return tools


def get_tools_openai() -> list[dict]:
    """Return tools in OpenAI function-calling format."""
    tools = []
    for info in TOOL_REGISTRY.values():
        tools.append({
            "type": "function",
            "function": {
                "name": info["name"],
                "description": info["description"],
                "parameters": info["input_schema"],
            }
        })
    return tools


def execute_tool(name: str, inputs: dict[str, Any]) -> dict[str, Any]:
    """Execute a registered tool by name."""
    if name not in TOOL_REGISTRY:
        return {"error": f"Unknown tool: {name}"}
    func = TOOL_REGISTRY[name]["func"]
    return func(**inputs)


# ============================================================
# Import tool modules to trigger registration
# ============================================================

from . import pdf_reader       # noqa: E402, F401
from . import web_search       # noqa: E402, F401
from . import enrichment       # noqa: E402, F401
from . import external_dbs     # noqa: E402, F401
