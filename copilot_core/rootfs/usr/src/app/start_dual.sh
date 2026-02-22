#!/bin/sh
# PilotSuite Core v4.0.0 + Ollama startup script
# Ollama is bundled in the addon for offline LLM support.
# Models are persisted in /share/ (NOT /data/) to avoid bloating HA backups.
#
# Model strategy:
#   - qwen3:0.6b (400MB) is ALWAYS pulled (obligatory, guarantees offline AI)
#   - qwen3:4b (2.5GB) is the recommended default (pulled if configured)

set -e

echo "============================================"
echo "  PilotSuite v7.7.3 -- Styx"
echo "  Die Verbindung beider Welten"
echo "  Local AI for your Smart Home"
echo "============================================"

# ---------------------------------------------------------------------------
# Bridge: Read /data/options.json and export env vars
# This ensures addon configuration from HA UI reaches both the shell script
# (for Ollama model selection) and Python (via core_setup.py).
# ---------------------------------------------------------------------------
OPTIONS_FILE="/data/options.json"
if [ -f "$OPTIONS_FILE" ]; then
    echo "Loading addon configuration from $OPTIONS_FILE..."

    # Extract configuration via Python (jq not available on Alpine base)
    eval "$(python3 -c "
import json, os
try:
    with open('$OPTIONS_FILE') as f:
        opts = json.load(f)
    pairs = {
        'OLLAMA_URL': opts.get('conversation_ollama_url', ''),
        'OLLAMA_MODEL': opts.get('conversation_ollama_model', ''),
        'CONVERSATION_ENABLED': str(opts.get('conversation_enabled', True)).lower(),
        'ASSISTANT_NAME': opts.get('conversation_assistant_name', ''),
    }
    # Log level
    ll = opts.get('log_level', '')
    if ll:
        pairs['LOG_LEVEL'] = ll
    # Auth token
    at = opts.get('auth_token', '')
    if at:
        pairs['AUTH_TOKEN'] = at

    for k, v in pairs.items():
        if v:
            print(f'export {k}=\"{v}\"')
except Exception as e:
    print(f'echo \"WARNING: Could not parse {chr(36)}OPTIONS_FILE: {e}\"', flush=True)
" 2>/dev/null)" || echo "WARNING: Config bridge failed, using defaults"
else
    echo "No $OPTIONS_FILE found (development mode), using env defaults"
fi

# Obligatory minimum model (always available, 400MB)
FALLBACK_MODEL="qwen3:0.6b"

# Recommended model (configurable via addon options -> env var)
MODEL=${OLLAMA_MODEL:-qwen3:4b}

# Ensure model persistence directory exists
export OLLAMA_MODELS=${OLLAMA_MODELS:-/share/pilotsuite/ollama/models}
mkdir -p "$OLLAMA_MODELS" 2>/dev/null || echo "WARNING: Cannot create $OLLAMA_MODELS (is /share mounted?)"

echo "Configuration: model=$MODEL, ollama_url=${OLLAMA_URL:-http://localhost:11434}"

# Check if Ollama is installed
if ! command -v ollama >/dev/null 2>&1; then
    echo "WARNING: Ollama not found -- LLM features disabled, starting API only"
    exec python3 -u main.py
fi

# Start Ollama server in background
echo "Starting Ollama service (models dir: $OLLAMA_MODELS)..."
ollama serve &
OLLAMA_PID=$!

# Cleanup on exit: kill Ollama when main process ends
cleanup() {
    echo "Shutting down Ollama (PID $OLLAMA_PID)..."
    kill "$OLLAMA_PID" 2>/dev/null || true
    wait "$OLLAMA_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Wait for Ollama to be ready (max 60s with exponential backoff)
echo "Waiting for Ollama..."
READY=false
WAIT=1
TOTAL_WAIT=0
MAX_WAIT=60
while [ "$TOTAL_WAIT" -lt "$MAX_WAIT" ]; do
    if curl -sf -m 3 http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "Ollama is ready! (after ${TOTAL_WAIT}s)"
        READY=true
        break
    fi
    echo "    Waiting... (${TOTAL_WAIT}s/${MAX_WAIT}s)"
    sleep "$WAIT"
    TOTAL_WAIT=$((TOTAL_WAIT + WAIT))
    # Exponential backoff: 1, 2, 4, 4, 4...
    [ "$WAIT" -lt 4 ] && WAIT=$((WAIT * 2))
done

if [ "$READY" = "false" ]; then
    echo "WARNING: Ollama did not start within ${MAX_WAIT}s -- LLM features may be unavailable"
fi

# Model pull helper (idempotent, uses ollama pull which is safe to call multiple times)
pull_model() {
    TARGET_MODEL="$1"
    LABEL="$2"
    echo "Ensuring $LABEL model $TARGET_MODEL is available..."
    if ollama pull "$TARGET_MODEL" 2>&1; then
        echo "$LABEL model $TARGET_MODEL ready"
        return 0
    else
        echo "WARNING: Could not pull $LABEL model $TARGET_MODEL"
        return 1
    fi
}

# Model pull strategy
if [ "$READY" = "true" ]; then
    # 1) OBLIGATORY: Always ensure fallback model is available
    pull_model "$FALLBACK_MODEL" "fallback" || true

    # 2) RECOMMENDED: Pull configured model if different from fallback
    if [ "$MODEL" != "$FALLBACK_MODEL" ]; then
        if ! pull_model "$MODEL" "configured"; then
            echo "INFO: Falling back to $FALLBACK_MODEL"
            export OLLAMA_MODEL="$FALLBACK_MODEL"
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
