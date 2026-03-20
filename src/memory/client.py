"""OpenMemory client — retrieve and store memories for Arkadia."""

import os
import httpx

MEMORY_URL = os.getenv("OPENMEMORY_URL", "https://memory.arkadia.network")


async def retrieve_memories(query: str, limit: int = 10) -> list[str]:
    """Retrieve relevant memories based on a query."""
    try:
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            response = await client.post(
                f"{MEMORY_URL}/lgm/retrieve",
                json={
                    "query": query,
                    "node": "plan",
                    "namespace": "default",
                    "limit": limit,
                },
            )
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                return [
                    item.get("content", str(item))
                    for item in items
                    if item
                ]
    except Exception as e:
        print(f"[Memory] Retrieve failed: {type(e).__name__}: {e}")
    return []


async def store_memory(content: str, node: str = "observe", metadata: dict = None) -> bool:
    """Store a memory in OpenMemory."""
    try:
        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            payload = {
                "content": content,
                "node": node,
                "namespace": "default",
            }

            response = await client.post(
                f"{MEMORY_URL}/lgm/store",
                json=payload,
            )
            return response.status_code == 200
    except Exception as e:
        print(f"[Memory] Store failed: {type(e).__name__}: {e}")
    return False
