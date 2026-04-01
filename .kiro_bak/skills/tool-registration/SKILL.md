# MCP Tool Registration

## Pattern
```python
from mcp.server import FastMCP

server = FastMCP("pyfastmail-mcp")

@server.tool()
async def tool_name(param: str, optional_param: int = 10) -> str:
    """Clear description of what this tool does."""
    # Tools return strings (JSON formatted for structured data)
    return json.dumps(result, indent=2)
```

## Guidelines
- Tool functions are async.
- Use type hints on all parameters — MCP uses them to generate the schema.
- Default values define optional parameters.
- Return `str` always. Use `json.dumps` for structured data.
- Tool description (docstring) should be clear enough for an LLM to know when to use it.
- Keep tool functions thin: validate → call client → format response.
- Handle errors gracefully — return error messages, don't raise exceptions to the MCP layer.

## Registration Pattern (per module)
```python
def register(server: FastMCP, client: JMAPClient):
    @server.tool()
    async def my_tool(...) -> str:
        ...
```
