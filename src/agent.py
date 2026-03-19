"""Arkadia's LangGraph agent — router + domain nodes + persona chat."""

import json
from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from src.persona.system_prompt import SYSTEM_PROMPT
from src.router import route_message
from src.mcp_client import get_mcp_tools, call_mcp_tool


class AgentState(TypedDict):
    """The state that flows through Arkadia's graph."""
    messages: Annotated[list, add_messages]
    domains: list[str]
    tool_results: list[str]

def create_llm(base_url: str, model: str) -> ChatOpenAI:
    """Create the LLM client pointing at vLLM."""
    return ChatOpenAI(
        openai_api_base=base_url,
        openai_api_key="not-needed",
        model_name=model,
        temperature=0.7,
        streaming=True,
        model_kwargs={
            "extra_body": {
                "chat_template_kwargs": {
                    "enable_thinking": False
                }
            }
        },
    )

_llm = None


def set_llm(llm: ChatOpenAI):
    global _llm
    _llm = llm


async def router_node(state: AgentState, config: RunnableConfig) -> dict:
    """Classify the user's message into one or more domains."""
    last_message = state["messages"][-1]
    content = last_message.content if hasattr(last_message, "content") else str(last_message)
    domains = await route_message(content, _llm)
    return {"domains": domains, "tool_results": []}


async def domain_node(state: AgentState, config: RunnableConfig) -> dict:
    """For each active domain, list tools, ask the LLM to pick one, execute it."""
    domains = [d for d in state.get("domains", []) if d != "general"]
    if not domains:
        return {"tool_results": []}

    last_message = state["messages"][-1]
    user_content = last_message.content if hasattr(last_message, "content") else str(last_message)
    results = []

    for domain in domains:
        tools = await get_mcp_tools(domain)
        if not tools:
            continue

        tool_prompt = (
            f"You have access to these tools for the '{domain}' domain:\n"
            f"{json.dumps(tools, indent=2)}\n\n"
            f"User request: {user_content}\n\n"
            "If a tool call is needed, respond with ONLY a JSON object: "
            '{"tool": "tool_name", "arguments": {...}}\n'
            "If no tool call is needed, respond with: {\"tool\": null}"
        )

        response = await _llm.ainvoke([HumanMessage(content=tool_prompt)])
        response_text = response.content.strip()

        try:
            parsed = json.loads(response_text)
            if parsed.get("tool"):
                result = await call_mcp_tool(domain, parsed["tool"], parsed.get("arguments", {}))
                results.append(f"[{domain}] {parsed['tool']}: {result}")
        except (json.JSONDecodeError, TypeError):
            pass

    return {"tool_results": results}


async def chat_node(state: AgentState, config: RunnableConfig) -> dict:
    """Generate the final response with Arkadia's persona."""
    messages = list(state["messages"])
    tool_results = state.get("tool_results", [])

    system_content = SYSTEM_PROMPT
    if tool_results:
        system_content += (
            "\n\n## Tool results from this turn\n"
            "Use ONLY these results to inform your response. "
            "NEVER invent, fabricate, or embellish data beyond what is provided here. "
            "If the results are sparse, say so honestly — don't fill gaps with imagination. "
            "Summarise naturally — don't dump raw data.\n\n"
            + "\n".join(tool_results)
        )

    system_msg = SystemMessage(content=system_content)
    response = await _llm.ainvoke([system_msg] + messages)
    return {"messages": [response]}


def should_use_tools(state: AgentState) -> str:
    """Route to domain node or straight to chat."""
    domains = state.get("domains", ["general"])
    if all(d == "general" for d in domains):
        return "chat"
    return "domain"


def build_graph(checkpointer=None):
    """Build Arkadia's routed agent graph."""
    graph = StateGraph(AgentState)

    graph.add_node("router", router_node)
    graph.add_node("domain", domain_node)
    graph.add_node("chat", chat_node)

    graph.add_edge(START, "router")
    graph.add_conditional_edges("router", should_use_tools, {"domain": "domain", "chat": "chat"})
    graph.add_edge("domain", "chat")
    graph.add_edge("chat", END)

    return graph.compile(checkpointer=checkpointer)
