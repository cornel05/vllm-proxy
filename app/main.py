import time
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vllm-proxy")

# ── Prometheus Metrics (per-IP labels) ──────────────────────────────

REQUEST_COUNT = Counter(
    "vllm_proxy_requests_total",
    "Total requests forwarded to vLLM",
    ["client_ip", "endpoint", "status_code", "method"],
)

ERROR_COUNT = Counter(
    "vllm_proxy_errors_total",
    "Total failed requests",
    ["client_ip", "endpoint", "error_type"],
)

REQUEST_LATENCY = Histogram(
    "vllm_proxy_request_duration_seconds",
    "Request latency in seconds",
    ["client_ip", "endpoint"],
    buckets=[0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120],
)

PROMPT_TOKENS = Counter(
    "vllm_proxy_prompt_tokens_total",
    "Total prompt tokens consumed",
    ["client_ip", "endpoint", "model"],
)

COMPLETION_TOKENS = Counter(
    "vllm_proxy_completion_tokens_total",
    "Total completion tokens consumed",
    ["client_ip", "endpoint", "model"],
)

ACTIVE_REQUESTS = Gauge(
    "vllm_proxy_active_requests",
    "Currently in-flight requests",
    ["client_ip"],
)


# ── HTTP client lifecycle ───────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(
        base_url=settings.vllm_base_url,
        timeout=httpx.Timeout(settings.request_timeout),
    )
    logger.info(f"Proxy started → target: {settings.vllm_base_url}")
    yield
    await app.state.http_client.aclose()


app = FastAPI(title="vLLM Proxy", lifespan=lifespan)


# ── Helpers ─────────────────────────────────────────────────────────

def get_client_ip(request: Request) -> str:
    """Extract real client IP from X-Forwarded-For (set by Nginx)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


def extract_token_usage(body: dict) -> dict:
    """Pull usage stats from OpenAI-compatible response."""
    usage = body.get("usage", {})
    return {
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "model": body.get("model", "unknown"),
    }


# ── Metrics endpoint (for Prometheus scraping) ──────────────────────

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ── Health check ────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Catch-all proxy ────────────────────────────────────────────────

PROXY_PATHS = [
    "/v1/chat/completions",
    "/v1/completions",
    "/v1/embeddings",
    "/v1/models",
]


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(request: Request, path: str):
    client_ip = get_client_ip(request)
    endpoint = f"/{path}"
    client: httpx.AsyncClient = request.app.state.http_client

    ACTIVE_REQUESTS.labels(client_ip=client_ip).inc()
    start = time.perf_counter()

    try:
        # Build upstream request
        body = await request.body()
        headers = {
            k: v
            for k, v in request.headers.items()
            if k.lower() not in ("host", "x-forwarded-for")
        }

        upstream_resp = await client.request(
            method=request.method,
            url=f"/{path}",
            content=body,
            headers=headers,
        )

        duration = time.perf_counter() - start

        # Record base metrics
        REQUEST_COUNT.labels(
            client_ip=client_ip,
            endpoint=endpoint,
            status_code=upstream_resp.status_code,
            method=request.method,
        ).inc()

        REQUEST_LATENCY.labels(
            client_ip=client_ip,
            endpoint=endpoint,
        ).observe(duration)

        # Record error if non-2xx
        if upstream_resp.status_code >= 400:
            ERROR_COUNT.labels(
                client_ip=client_ip,
                endpoint=endpoint,
                error_type=f"http_{upstream_resp.status_code}",
            ).inc()

        # Parse token usage from JSON responses
        content_type = upstream_resp.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                resp_json = upstream_resp.json()
                usage = extract_token_usage(resp_json)
                if usage["prompt_tokens"] or usage["completion_tokens"]:
                    PROMPT_TOKENS.labels(
                        client_ip=client_ip,
                        endpoint=endpoint,
                        model=usage["model"],
                    ).inc(usage["prompt_tokens"])
                    COMPLETION_TOKENS.labels(
                        client_ip=client_ip,
                        endpoint=endpoint,
                        model=usage["model"],
                    ).inc(usage["completion_tokens"])
            except Exception:
                pass  # Non-JSON or malformed — skip token tracking

        # Return response to client
        return Response(
            content=upstream_resp.content,
            status_code=upstream_resp.status_code,
            headers=dict(upstream_resp.headers),
        )

    except httpx.TimeoutException:
        duration = time.perf_counter() - start
        ERROR_COUNT.labels(
            client_ip=client_ip, endpoint=endpoint, error_type="timeout"
        ).inc()
        REQUEST_LATENCY.labels(client_ip=client_ip, endpoint=endpoint).observe(duration)
        return JSONResponse({"error": "upstream timeout"}, status_code=504)

    except httpx.ConnectError:
        ERROR_COUNT.labels(
            client_ip=client_ip, endpoint=endpoint, error_type="connect_error"
        ).inc()
        return JSONResponse({"error": "cannot reach vLLM"}, status_code=502)

    except Exception as e:
        ERROR_COUNT.labels(
            client_ip=client_ip, endpoint=endpoint, error_type="internal"
        ).inc()
        logger.exception(f"Proxy error: {e}")
        return JSONResponse({"error": "internal proxy error"}, status_code=500)

    finally:
        ACTIVE_REQUESTS.labels(client_ip=client_ip).dec()
