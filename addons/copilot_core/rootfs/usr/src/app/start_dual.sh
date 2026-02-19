#!/bin/sh
# PilotSuite Core v3.7.0 + Ollama startup script
# Ollama is bundled in the addon for offline LLM support.
# Models are persisted in /share/ (NOT /data/) to avoid bloating HA backups.
#
# Model strategy:
#   - qwen3:0.6b (400MB) is ALWAYS pulled (obligatory, guarantees offline AI)
#   - qwen3:4b (2.5GB) is the recommended default (pulled if configured)

set -e

echo "============================================"
echo "  PilotSuite v3.7.0 -- Styx"
echo "  Die Verbindung beider Welten"
echo "  Local AI for your Smart Home"
echo "============================================"

# Obligatory minimum model (always available, 400MB)
FALLBACK_MODEL="qwen3:0.6b"

# Recommended model (configurable via addon options -> env var)
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

# Model pull strategy
if [ "$READY" = "true" ]; then
    # 1) OBLIGATORY: Always ensure fallback model is available
    FALLBACK_BASE=$(echo "$FALLBACK_MODEL" | cut -d: -f1)
    if ollama list 2>/dev/null | grep -q "$FALLBACK_BASE"; then
        echo "Fallback model $FALLBACK_MODEL available"
    else
        echo "Pulling obligatory fallback model $FALLBACK_MODEL (400MB, ensures offline AI)..."
        if ollama pull "$FALLBACK_MODEL"; then
            echo "Fallback model $FALLBACK_MODEL ready"
        else
            echo "WARNING: Could not pull fallback model -- offline AI may be limited"
        fi
    fi

    # 2) RECOMMENDED: Pull configured model if different from fallback
    if [ "$MODEL" != "$FALLBACK_MODEL" ]; then
        MODEL_BASE=$(echo "$MODEL" | cut -d: -f1)
        if ollama list 2>/dev/null | grep -q "$MODEL_BASE"; then
            echo "Configured model $MODEL available"
        else
            echo "Pulling recommended model $MODEL (this may take a few minutes)..."
            if ollama pull "$MODEL"; then
                echo "Model $MODEL downloaded successfully"
            else
                echo "INFO: Could not pull $MODEL -- using fallback $FALLBACK_MODEL"
                export OLLAMA_MODEL="$FALLBACK_MODEL"
            fi
        fi
    fi
fi

echo ""
echo "Starting PilotSuite Core API on port ${PORT:-8909}..."
echo "Dashboard: http://localhost:${PORT:-8909}/"
echo "API Docs:  http://localhost:${PORT:-8909}/api/v1/docs/"
echo "Chat API:  http://localhost:${PORT:-8909}/v1/chat/completions"
echo "MCP:       http://localhost:${PORT:-8909}/mcp"
echo "============================================"
exec python3 -u main.py
