#!/bin/bash
# Test script - sends requests to the proxy via Ollama
# Usage: ./test.sh [PROXY_URL]

PROXY_URL="${1:-http://localhost:8080}"

echo "=== vLLM Proxy Test (via Ollama) ==="
echo "Target: $PROXY_URL"
echo ""

# 1. Health check
echo "── Health Check ──"
curl -s "$PROXY_URL/health" | python3 -m json.tool
echo ""

# 2. Chat completion via Ollama OpenAI API
echo "── Chat Completion (Ollama via Proxy) ──"
curl -s "$PROXY_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "phi",
    "messages": [{"role": "user", "content": "Hello, what is 2+2?"}],
    "temperature": 0.7,
    "stream": false
  }' | python3 -m json.tool
echo ""

# 3. Send multiple requests to generate metrics
echo "── Sending 5 requests for metrics ──"
for i in $(seq 1 5); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$PROXY_URL/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d "{\"model\": \"phi\", \"messages\": [{\"role\": \"user\", \"content\": \"Request $i: Tell me a short joke\"}], \"max_tokens\": 50, \"stream\": false}")
  echo "  Request $i: HTTP $STATUS"
  sleep 1
done
echo ""

# 4. Check metrics endpoint
echo "── Proxy Metrics Sample ──"
curl -s "$PROXY_URL/metrics" | grep -E "^vllm_proxy_" | head -20
echo ""
echo "=== Done ==="
echo "View full metrics: $PROXY_URL/metrics"

