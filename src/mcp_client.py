"""MCP client — connects to MCP servers and executes tool calls."""

import os
import json
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

from src.domains import DOMAIN_CONFIG


def _resolve_headers(headers: dict | None) -> dict | None:
    """Replace ${ENV_VAR} placeholders in header values."""
    if not headers:
        return None
    resolved = {}
    for key, value in headers.items():
        if value.startswith("${") and value.endswith("}"):
            env_name = value[2:-1]
            resolved[key] = os.getenv(env_name, "")
        else:
            resolved[key] = value
    return resolved


async def get_mcp_tools(domain: str) -> list[dict]:
    """Connect to an MCP server and return its tools as LangChain-compatible dicts."""
    config = DOMAIN_CONFIG.get(domain)
    if not config:
        return []

    tools = []
    headers = _resolve_headers(config.get("headers"))

    try:
        if config["transport"] == "sse":
            async with sse_client(config["mcp_url"], headers=headers) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    tools = result.tools
        else:
            async with streamablehttp_client(config["mcp_url"], headers=headers) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    tools = result.tools
    except Exception as e:
        print(f"[MCP] Failed to list tools from {config['name']}: {e}")
        return []

    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema if tool.inputSchema else {"type": "object", "properties": {}},
            },
        }
        for tool in tools
    ]


async def call_mcp_tool(domain: str, tool_name: str, arguments: dict) -> Any:
    """Execute a tool call against an MCP server and return the result."""
    config = DOMAIN_CONFIG.get(domain)
    if not config:
        return {"error": f"Unknown domain: {domain}"}

    headers = _resolve_headers(config.get("headers"))

    try:
        if config["transport"] == "sse":
            async with sse_client(config["mcp_url"], headers=headers) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
                    return _extract_result(result)
        else:
            async with streamablehttp_client(config["mcp_url"], headers=headers) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
                    return _extract_result(result)
    except Exception as e:
        return {"error": f"MCP tool call failed: {e}"}


def _extract_result(result) -> str:
    """Extract text content from an MCP tool result."""
    if hasattr(result, "content") and result.content:
        parts = []
        for block in result.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "\n".join(parts) if parts else str(result)
    return str(result)
```

We also need to add the `mcp` package to `requirements.txt`. Update it to:
```
langgraph>=1.1.0
langchain-openai>=0.3.0
langgraph-checkpoint-postgres>=3.0.0
psycopg[binary]>=3.0.0
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
httpx>=0.28.0
mcp>=1.0.0
