# vLLM Proxy — Per-IP Metrics Gateway

FastAPI reverse proxy for vLLM that tracks per-IP metrics (request count, token usage, latency, errors) and exposes them to Prometheus/Grafana.

## Architecture

```
Client → Nginx (:8080) → FastAPI Proxy (:8000) → vLLM (:30154)
                              ↓
                         /metrics endpoint
                              ↓
                    Prometheus → Grafana (:3000)
```

## Quick Start (with mock vLLM for testing)

```bash
# Start everything including mock vLLM
docker compose --profile test up -d --build

# Test it
./test.sh

# Open Grafana
# http://localhost:3000  (admin / admin)
# Dashboard: "vLLM Proxy - Per IP Metrics"
```

## Production Deploy (real vLLM)

1. Edit `docker-compose.prod.yml` — set `VLLM_PROXY_VLLM_BASE_URL` to your vLLM address
2. Run:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```
3. Tell users to call `http://<this-server>:8080/v1/chat/completions` instead of vLLM directly

### Integrate with existing Prometheus

Add this scrape config to your Prometheus:

```yaml
- job_name: "vllm-proxy"
  static_configs:
    - targets: ["<proxy-server-ip>:8000"]
```

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
├── mock_vllm/
│   └── server.py        # Mock vLLM for testing
├── grafana/
│   ├── dashboards/      # Pre-built dashboard JSON
│   └── provisioning/    # Auto-config datasource + dashboard
├── docker-compose.yml       # Full stack (with mock, Prometheus, Grafana)
├── docker-compose.prod.yml  # Production (proxy + nginx only)
├── prometheus.yml           # Prometheus scrape config
└── test.sh                  # Test script
```
