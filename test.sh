#!/bin/bash
# Test script - sends requests to the proxy simulating different client IPs
# Usage: ./test.sh [PROXY_URL]

PROXY_URL="${1:-http://localhost:8080}"

echo "=== vLLM Proxy Test ==="
echo "Target: $PROXY_URL"
echo ""

# 1. Health check
echo "── Health Check ──"
curl -s "$PROXY_URL/health" | python3 -m json.tool
echo ""

# 2. List models
echo "── List Models ──"
curl -s "$PROXY_URL/v1/models" | python3 -m json.tool
echo ""

# 3. Chat completion (normal)
echo "── Chat Completion ──"
curl -s "$PROXY_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-3.5-27b",
    "messages": [{"role": "user", "content": "Hello, how are you?"}],
    "max_tokens": 100
  }' | python3 -m json.tool
echo ""

# 4. Send multiple requests to generate metrics
echo "── Sending 10 requests for metrics ──"
for i in $(seq 1 10); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$PROXY_URL/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d "{\"model\": \"qwen-3.5-27b\", \"messages\": [{\"role\": \"user\", \"content\": \"Request $i\"}]}")
  echo "  Request $i: HTTP $STATUS"
done
echo ""

# 5. Check metrics
echo "── Proxy Metrics ──"
curl -s "$PROXY_URL/metrics" | grep -E "^vllm_proxy_" | head -30
echo ""
echo "=== Done ==="
