#!/bin/bash
# PilotSuite Core startup with embedded Ollama support (alternative script)
# Use start_dual.sh as the primary startup script.

set -e

echo "Starting PilotSuite Core..."

# Ensure model persistence
export OLLAMA_MODELS=${OLLAMA_MODELS:-/data/ollama/models}
mkdir -p "$OLLAMA_MODELS"

NEED_OLLAMA=${CONVERSATION_ENABLED:-false}

if [ "$NEED_OLLAMA" = "true" ]; then
    echo "Checking Ollama..."

    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "Starting Ollama service..."

        ollama serve &
        OLLAMA_PID=$!

        echo "Waiting for Ollama..."
        for i in {1..30}; do
            if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
                echo "Ollama is ready!"
                break
            fi
            sleep 1
        done

        MODEL=${OLLAMA_MODEL:-lfm2.5-thinking}
        echo "Ensuring model $MODEL exists..."
        ollama pull "$MODEL" || echo "WARNING: Failed to pull $MODEL"
    else
        echo "Ollama already running"
    fi
fi

echo "Starting PilotSuite Core API on port ${PORT:-8909}..."
exec python3 -u main.py
