#!/bin/bash
# PilotSuite Core startup with embedded Ollama support

set -e

echo "🚀 Starting PilotSuite Core..."

# Check if Ollama is needed
NEED_OLLAMA=${CONVERSATION_ENABLED:-false}

if [ "$NEED_OLLAMA" = "true" ]; then
    echo "🤖 Checking Ollama..."
    
    # Check if Ollama is running
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "🤖 Starting Ollama service..."
        
        # Start Ollama in background
        ollama serve &
        OLLAMA_PID=$!
        
        # Wait for Ollama to be ready
        echo "🤖 Waiting for Ollama..."
        for i in {1..30}; do
            if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
                echo "🤖 Ollama is ready!"
                break
            fi
            sleep 1
        done
        
        # Pull model if not exists
        MODEL=${OLLAMA_MODEL:-deepseek-r1}
        echo "🤖 Ensuring model $MODEL exists..."
        ollama pull $MODEL || true
    else
        echo "🤖 Ollama already running"
    fi
fi

echo "🚀 Starting PilotSuite Core API..."
exec python3 -u main.py
