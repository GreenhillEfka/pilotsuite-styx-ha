#!/bin/sh
# PilotSuite Core + Ollama startup script
# Ollama is bundled in the addon for offline LLM support.
# Models are persisted in /share/ (NOT /data/) to avoid bloating HA backups.

set -e

echo "Starting PilotSuite Core with Ollama..."

# Model to use (configurable via addon options -> env var)
MODEL=${OLLAMA_MODEL:-qwen3:4b}

# Ensure model persistence directory exists
export OLLAMA_MODELS=${OLLAMA_MODELS:-/share/ai_home_copilot/ollama/models}
mkdir -p "$OLLAMA_MODELS"

# Check if Ollama is installed
if ! command -v ollama >/dev/null 2>&1; then
    echo "WARNING: Ollama not found -- LLM features disabled, starting API only"
    exec python3 -u main.py
fi

# Start Ollama server in background
echo "Starting Ollama service (models dir: $OLLAMA_MODELS)..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready (max 30s)
echo "Waiting for Ollama..."
READY=false
for i in $(seq 1 15); do
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "Ollama is ready!"
        READY=true
        break
    fi
    echo "    Waiting... ($i/15)"
    sleep 2
done

if [ "$READY" = "false" ]; then
    echo "WARNING: Ollama did not start within 30s -- LLM features may be unavailable"
fi

# Pull model if not already available (first-run only, cached afterwards)
if [ "$READY" = "true" ]; then
    echo "Checking model: $MODEL"
    # Use ollama list to check; the model name might have :latest suffix
    MODEL_BASE=$(echo "$MODEL" | cut -d: -f1)
    if ollama list 2>/dev/null | grep -q "$MODEL_BASE"; then
        echo "Model $MODEL already available"
    else
        echo "Pulling model $MODEL (first run -- this may take a few minutes)..."
        if ollama pull "$MODEL"; then
            echo "Model $MODEL downloaded successfully"
        else
            echo "WARNING: Failed to pull $MODEL -- check network connectivity"
            echo "You can manually pull later: ollama pull $MODEL"
        fi
    fi
fi

echo "Starting PilotSuite Core API on port ${PORT:-8909}..."
exec python3 -u main.py
