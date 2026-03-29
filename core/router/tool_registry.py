"""Tool registry — dynamic tool loading from plugins."""

import logging
from typing import Dict, Callable, Any, List

log = logging.getLogger("localisa.router.registry")


class Tool:
    """A registered tool that the LLM can call."""

    def __init__(self, name: str, description: str, handler: Callable, parameters: Dict[str, Any] = None):
        self.name = name
        self.description = description
        self.handler = handler
        self.parameters = parameters or {}

    def to_llm_schema(self) -> Dict:
        """Convert to OpenAI function-calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                },
            },
        }

    def to_description(self) -> str:
        """One-line description for simple routing."""
        params = ", ".join(self.parameters.keys()) if self.parameters else ""
        return f"- {self.name}({params}): {self.description}"


class ToolRegistry:
    """Central registry for all available tools."""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, name: str, description: str, handler: Callable, parameters: Dict = None):
        """Register a tool."""
        self.tools[name] = Tool(name, description, handler, parameters)
        log.info(f"Registered tool: {name}")

    def get(self, name: str) -> Tool:
        return self.tools.get(name)

    def list_tools(self) -> List[Tool]:
        return list(self.tools.values())

    def get_llm_tools(self) -> List[Dict]:
        """Get all tools in OpenAI function-calling format."""
        return [t.to_llm_schema() for t in self.tools.values()]

    def get_descriptions(self) -> str:
        """Get all tool descriptions for simple text-based routing."""
        return "\n".join(t.to_description() for t in self.tools.values())

    async def execute(self, name: str, **kwargs) -> Any:
        """Execute a tool by name."""
        tool = self.tools.get(name)
        if not tool:
            return {"error": f"Unknown tool: {name}"}
        try:
            import asyncio
            if asyncio.iscoroutinefunction(tool.handler):
                return await tool.handler(**kwargs)
            else:
                return tool.handler(**kwargs)
        except Exception as e:
            log.error(f"Tool {name} failed: {e}")
            return {"error": str(e)}


# Global registry
registry = ToolRegistry()
