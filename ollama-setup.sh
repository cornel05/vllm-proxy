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

# Find Ollama container name
OLLAMA_CONTAINER=$(docker ps --filter "ancestor=ollama/ollama" --format "{{.Names}}" | head -1)
if [ -z "$OLLAMA_CONTAINER" ]; then
  OLLAMA_CONTAINER=$(docker ps --filter "name=ollama" --format "{{.Names}}" | head -1)
fi

if [ -z "$OLLAMA_CONTAINER" ]; then
  echo "✗ Cannot find Ollama container"
  exit 1
fi

echo ""
echo "Pulling model: $MODEL via container '$OLLAMA_CONTAINER' ..."
echo "(This may take a few minutes on first run)"
docker exec "$OLLAMA_CONTAINER" ollama pull "$MODEL"

PULL_EXIT=$?
if [ $PULL_EXIT -ne 0 ]; then
  echo "✗ Failed to pull model (exit code: $PULL_EXIT)"
  exit 1
fi

echo ""
echo "✓ Model pulled. Available models:"
docker exec "$OLLAMA_CONTAINER" ollama list
echo ""
echo "=== Setup Complete ==="
echo "Proxy: http://localhost:8081/v1/chat/completions"
echo "Grafana: http://localhost:3000 (admin/admin)"