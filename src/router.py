"""Domain router — classifies user messages into MCP domains."""

import json
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

ROUTER_PROMPT = """You are a message classifier for a smart home AI assistant called Arkadia.

Given a user message, identify which domains are needed to respond. Return ONLY a JSON array of domain strings, nothing else.

Available domains:
- "smart_home" — lights, switches, sensors, automations, Home Assistant
- "media" — Plex, movies, TV shows, music, playback
- "dns" — Pi-hole, DNS, ad blocking, network queries, domains
- "infrastructure" — Proxmox, VMs, containers, cluster, servers, hardware
- "automation" — N8N workflows, scheduled tasks, triggers
- "storage" — TrueNAS, pools, datasets, snapshots, shares, disks, SMART health, alerts, replication, scrubs
- "deployment" — Coolify, deployments, containers, services, applications, environment variables
- "general" — casual chat, questions, anything not matching above

Rules:
- Always include at least one domain
- Include "general" if the message needs a conversational response alongside tool actions
- A message like "turn on the lights and play some jazz" returns ["smart_home", "media"]
- A simple "hey how are you" returns ["general"]

User message: {message}"""


async def route_message(message: str, llm: ChatOpenAI) -> list[str]:
    """Classify a message into one or more domains."""
    prompt = ROUTER_PROMPT.format(message=message)
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    try:
        domains = json.loads(response.content.strip())
        if isinstance(domains, list):
            return domains
    except (json.JSONDecodeError, TypeError):
        pass
    
    return ["general"]
