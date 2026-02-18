#!/bin/sh
# PilotSuite Core + Ollama startup script

set -e

echo "🚀 Starting PilotSuite Core with Ollama..."

# Check if model needs to be pulled
MODEL=${OLLAMA_MODEL:-lfm2.5-thinking:latest}

# Try to start Ollama
echo "🤖 Starting Ollama service..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "🤖 Waiting for Ollama..."
for i in 1 2 3 4 5 6 7 8 9 10; do
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "🤖 Ollama is ready!"
        break
    fi
    echo "    Waiting... ($i/10)"
    sleep 2
done

# Check if model exists, pull if not
echo "🤖 Checking model: $MODEL"
if ! ollama list | grep -q "$MODEL"; then
    echo "🤖 Pulling model $MODEL..."
    ollama pull $MODEL
else
    echo "🤖 Model already available"
fi

echo "🚀 Starting PilotSuite Core API..."
exec python3 -u main.py
