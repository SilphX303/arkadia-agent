"""Arkadia's LangGraph agent — the core orchestration loop."""

from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableConfig

from src.persona.system_prompt import SYSTEM_PROMPT


class AgentState(TypedDict):
    """The state that flows through Arkadia's graph."""
    messages: Annotated[list, add_messages]


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


# Module-level LLM reference, set during startup
_llm = None

def set_llm(llm: ChatOpenAI):
    global _llm
    _llm = llm


async def chat_node(state: AgentState, config: RunnableConfig) -> dict:
    """The main chat node — sends messages to vLLM with Arkadia's persona."""
    messages = state["messages"]
    system_msg = {"role": "system", "content": SYSTEM_PROMPT}

    response = await _llm.ainvoke([system_msg] + messages)
    return {"messages": [response]}


def build_graph(checkpointer=None):
    """Build Arkadia's agent graph."""
    graph = StateGraph(AgentState)
    graph.add_node("chat", chat_node)
    graph.add_edge(START, "chat")
    graph.add_edge("chat", END)
    return graph.compile(checkpointer=checkpointer)
