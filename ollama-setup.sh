#!/bin/bash
# Setup script - wait for Ollama to be ready, then pull a model

OLLAMA_URL="http://localhost:11434"
MODEL="phi"  # Phi-2: tiny, fast, good for testing (~1.6GB)
MAX_WAIT=60

echo "=== Ollama Setup ==="
echo "Waiting for Ollama to be ready..."

# Wait for Ollama API
for i in $(seq 1 $MAX_WAIT); do
  if curl -s "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
    echo "✓ Ollama is ready"
    break
  fi
  if [ $i -eq $MAX_WAIT ]; then
    echo "✗ Timeout waiting for Ollama"
    exit 1
  fi
  echo -n "."
  sleep 1
done

echo ""
echo "Pulling model: $MODEL ..."
curl -s -X POST "$OLLAMA_URL/api/pull" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$MODEL\"}" | grep -o '"[^"]*"' | head -10

echo ""
echo "✓ Model pulled. Available models:"
curl -s "$OLLAMA_URL/api/tags" | python3 -m json.tool 2>/dev/null || echo "(curl failed)"
echo ""
echo "=== Setup Complete ==="
echo "Proxy: http://localhost:8080/v1/chat/completions"
echo "Grafana: http://localhost:3000 (admin/admin)"
