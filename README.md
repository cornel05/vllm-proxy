# vLLM Proxy — Per-IP Metrics Gateway

FastAPI reverse proxy for vLLM (or Ollama) that tracks per-IP metrics (request count, token usage, latency, errors) and exposes them to Prometheus/Grafana.

## Architecture

```
Client → Nginx (:8081) → FastAPI Proxy (:8000) → vLLM/Ollama (:11434 or :30154)
                              ↓
                         /metrics endpoint
                              ↓
                    Prometheus → Grafana (:3000)
```

## Quick Start (with Ollama + Phi-2 for testing)

```bash
# Start everything (Ollama, proxy, Grafana, Prometheus)
docker compose --profile test up -d --build

# Pull Phi-2 model to Ollama (first time, ~1.6GB, takes 5-10 min)
./ollama-setup.sh

# Test the proxy
./test.sh

# Open Grafana
# http://localhost:3000  (admin / admin)
# Dashboard: "vLLM Proxy - Per IP Metrics"
```

**Note:** First request will be slow (model inference). Subsequent requests faster. Check Grafana to see per-IP metrics in real-time.

## Production Deploy (real vLLM)

1. Edit `docker-compose.prod.yml` — set `VLLM_PROXY_VLLM_BASE_URL` to your vLLM address (e.g., `http://172.16.28.63:30154`)
2. Run:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```
3. Tell users to call `http://<this-server>:8081/v1/chat/completions` instead of vLLM directly

### Integrate with existing Prometheus

Add this scrape config to your Prometheus on `172.16.28.63`:

```yaml
- job_name: "vllm-proxy"
  static_configs:
    - targets: ["<proxy-server-ip>:8000"]
```

Then Grafana on `172.16.28.63` will automatically pick up the new metrics.

## Metrics Exposed

| Metric | Labels | Description |
|--------|--------|-------------|
| `vllm_proxy_requests_total` | client_ip, endpoint, status_code, method | Total requests |
| `vllm_proxy_errors_total` | client_ip, endpoint, error_type | Failed requests |
| `vllm_proxy_request_duration_seconds` | client_ip, endpoint | Latency histogram |
| `vllm_proxy_prompt_tokens_total` | client_ip, endpoint, model | Prompt tokens used |
| `vllm_proxy_completion_tokens_total` | client_ip, endpoint, model | Completion tokens |
| `vllm_proxy_active_requests` | client_ip | In-flight requests |

## Configuration

Environment variables (prefix `VLLM_PROXY_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `VLLM_PROXY_VLLM_BASE_URL` | `http://172.16.28.63:30154` | vLLM upstream URL |
| `VLLM_PROXY_REQUEST_TIMEOUT` | `120` | Upstream timeout (seconds) |

## Files

```
├── app/
│   ├── main.py          # FastAPI proxy + metrics
│   └── config.py        # Settings
├── nginx/
│   └── default.conf     # Nginx reverse proxy config
├── grafana/
│   ├── dashboards/      # Pre-built dashboard JSON
│   └── provisioning/    # Auto-config datasource + dashboard
├── docker-compose.yml       # Full stack (with Ollama, Prometheus, Grafana)
├── docker-compose.prod.yml  # Production (proxy + nginx only)
├── prometheus.yml           # Prometheus scrape config
├── ollama-setup.sh          # Pull Phi-2 model to Ollama
└── test.sh                  # Test script
```
