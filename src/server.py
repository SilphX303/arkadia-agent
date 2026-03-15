"""FastAPI server exposing Arkadia as an OpenAI-compatible API."""

import os
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from langchain_core.messages import HumanMessage, AIMessage

from src.agent import build_graph, create_llm, set_llm


# Config from environment
VLLM_URL = os.getenv("VLLM_URL", "http://10.0.26.11:8000/v1")
VLLM_MODEL = os.getenv("VLLM_MODEL", "Qwen/Qwen3.5-27B")

graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start up: build graph and LLM client."""
    global graph

    llm = create_llm(VLLM_URL, VLLM_MODEL)
    set_llm(llm)
    graph = build_graph()

    yield


app = FastAPI(title="Arkadia", lifespan=lifespan)


@app.get("/v1/models")
async def list_models():
    """OpenAI-compatible model listing."""
    return {
        "object": "list",
        "data": [
            {
                "id": "arkadia",
                "object": "model",
                "owned_by": "arkadia-network",
            }
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """OpenAI-compatible chat completions endpoint."""
    body = await request.json()

    messages = []
    for msg in body.get("messages", []):
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    stream = body.get("stream", False)
    config = {"configurable": {"thread_id": "stateless"}}

    if stream:
        return StreamingResponse(
            stream_response(messages, config),
            media_type="text/event-stream",
        )
    else:
        result = await graph.ainvoke({"messages": messages}, config=config)
        content = result["messages"][-1].content
        return JSONResponse({
            "id": "chatcmpl-arkadia",
            "object": "chat.completion",
            "model": "arkadia",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
        })


async def stream_response(messages: list, config: dict):
    """Stream tokens back in OpenAI SSE format."""
    async for event in graph.astream_events(
        {"messages": messages}, config=config, version="v2"
    ):
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if hasattr(chunk, "content") and chunk.content:
                data = {
                    "id": "chatcmpl-arkadia",
                    "object": "chat.completion.chunk",
                    "model": "arkadia",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": chunk.content},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(data)}\n\n"

    yield "data: [DONE]\n\n"


@app.get("/health")
async def health():
    return {"status": "ok", "name": "arkadia"}
