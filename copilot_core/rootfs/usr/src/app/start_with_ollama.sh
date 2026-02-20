#!/bin/bash
# PilotSuite Core startup with embedded Ollama support (alternative script)
# Use start_dual.sh as the primary startup script.

set -e

echo "Starting PilotSuite Core..."

# Ensure model persistence
export OLLAMA_MODELS=${OLLAMA_MODELS:-/share/pilotsuite/ollama/models}
mkdir -p "$OLLAMA_MODELS"

FALLBACK_MODEL="qwen3:0.6b"
MODEL=${OLLAMA_MODEL:-qwen3:4b}
NEED_OLLAMA=${CONVERSATION_ENABLED:-true}

if [ "$NEED_OLLAMA" = "true" ]; then
    echo "Checking Ollama..."

    if ! curl -sf -m 3 http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "Starting Ollama service..."

        ollama serve &
        OLLAMA_PID=$!

        # Cleanup on exit
        trap "kill $OLLAMA_PID 2>/dev/null || true" EXIT INT TERM

        echo "Waiting for Ollama..."
        READY=false
        for i in $(seq 1 30); do
            if curl -sf -m 3 http://localhost:11434/api/tags > /dev/null 2>&1; then
                echo "Ollama is ready!"
                READY=true
                break
            fi
            sleep 2
        done

        if [ "$READY" = "false" ]; then
            echo "WARNING: Ollama did not become ready within 60s"
        fi

        if [ "$READY" = "true" ]; then
            # Ensure fallback model
            echo "Ensuring fallback model $FALLBACK_MODEL..."
            ollama pull "$FALLBACK_MODEL" || echo "WARNING: Failed to pull fallback $FALLBACK_MODEL"

            # Pull configured model if different
            if [ "$MODEL" != "$FALLBACK_MODEL" ]; then
                echo "Ensuring configured model $MODEL..."
                ollama pull "$MODEL" || {
                    echo "WARNING: Failed to pull $MODEL, using fallback $FALLBACK_MODEL"
                    export OLLAMA_MODEL="$FALLBACK_MODEL"
                }
            fi
        fi
    else
        echo "Ollama already running"
    fi
fi

echo "Starting PilotSuite Core API on port ${PORT:-8909}..."
exec python3 -u main.py
