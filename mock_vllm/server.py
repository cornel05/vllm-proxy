"""Mock vLLM server for testing the proxy without access to real vLLM."""

import random
import time

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Mock vLLM")


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "qwen-3.5-27b"
    messages: list[Message]
    max_tokens: int = 256
    temperature: float = 0.7


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "qwen-3.5-27b",
                "object": "model",
                "owned_by": "local",
            }
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    # Simulate some latency
    delay = random.uniform(0.1, 0.5)
    time.sleep(delay)

    prompt_tokens = sum(len(m.content.split()) * 2 for m in req.messages)
    completion_tokens = random.randint(20, 150)

    return {
        "id": f"chatcmpl-mock-{random.randint(1000,9999)}",
        "object": "chat.completion",
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"Mock response (latency: {delay:.2f}s)",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


@app.get("/metrics")
async def metrics():
    return "# Mock vLLM metrics endpoint\n"
