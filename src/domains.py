"""Domain definitions — maps router classifications to MCP server endpoints."""

DOMAIN_CONFIG = {
    "smart_home": {
        "name": "Home Assistant",
        "mcp_url": "https://ha-mcp.arkadia.network/mcp",
        "transport": "streamable_http",
    },
    "media": {
        "name": "Plex",
        "mcp_url": "https://plex-mcp.arkadia.network/sse",
        "transport": "sse",
    },
    "dns": {
        "name": "Pi-hole",
        "mcp_url": "https://pihole-mcp.arkadia.network/sse",
        "transport": "sse",
    },
    "infrastructure": {
        "name": "Proxmox",
        "mcp_url": "https://proxmox-mcp.arkadia.network/mcp",
        "transport": "streamable_http",
    },
    "storage": {
    "description": "TrueNAS storage: pools, datasets, snapshots, shares, disks, SMART health, alerts, replication, scrubs",
    "mcp_url": "https://truenas-mcp.arkadia.network/mcp",
    "transport": "streamable_http",
    },
    "deployment": {
        "name": "Coolify",
        "mcp_url": "https://coolify-mcp.arkadia.network/mcp",
        "transport": "streamable_http",
    },
    "automation": {
        "name": "N8N",
        "mcp_url": "https://n8n.arkadia.network/mcp-server/http",
        "transport": "streamable_http",
        "headers": {
            "Authorization": "Bearer ${N8N_MCP_TOKEN}"
        },
    },
}
