# PilotSuite Core Add-on

## Overview

PilotSuite Core is the backend engine for the PilotSuite Home Assistant integration. It provides:

- **Brain Architecture**: 15 brain regions with neural sensors and synaptic connections
- **Local LLM**: Ollama-powered conversation agent (runs fully offline)
- **17 Hub Engines**: Scene Intelligence, Presence, Energy Advisor, Anomaly Detection, and more
- **135+ API Endpoints**: Full REST API at `/api/v1/hub/*`

## Setup

1. Install this add-on from the Add-on Store
2. Start the add-on (first start downloads the Ollama model ~400MB-2.5GB)
3. Install the [PilotSuite HACS Integration](https://github.com/GreenhillEfka/pilotsuite-styx-ha)
4. Add the integration via Settings > Devices & Services > Add Integration > PilotSuite

## Configuration

| Option | Default | Description |
|--------|---------|-------------|
| Log Level | `info` | Logging verbosity |
| Auth Token | _(empty)_ | Optional API auth token |
| Ollama URL | `http://localhost:11435` | Ollama server URL |
| Ollama Model | `qwen3:0.6b` | LLM model name (default) |
| Cloud API URL (Fallback) | _(empty)_ | Optional OpenAI-compatible fallback URL (z. B. `https://ollama.com/v1`) |
| Cloud API Key (Fallback) | _(empty)_ | API key for fallback cloud endpoint |
| Cloud Model (Fallback) | `gpt-4o-mini` | Fallback cloud model name (auf Ollama Cloud automatisch auf kompatibles Modell gemappt) |
| Prefer Local Ollama | `true` | Try local first, then cloud fallback |
| Assistant Name | `Styx` | AI assistant display name |
| Conversation Enabled | `true` | Enable chat feature |

## API

The Core API runs on port 8909. Key endpoints:

- `GET /api/v1/status` — System status
- `GET /api/v1/hub/brain` — Brain Architecture overview
- `GET /api/v1/hub/brain/graph` — Brain graph (nodes + edges)
- `POST /v1/chat/completions` — OpenAI-compatible chat API
- `GET /health` — Health check

## Troubleshooting

- **Add-on won't start**: Check Supervisor logs for build errors
- **LLM not responding**: Model pulls run in background; trigger `POST /api/v1/agent/self-heal` and re-check `/chat/status`
- **Model not found (`gpt-4o-mini`)**: Set `conversation_cloud_*` fallback options and use the right endpoint (`https://ollama.com/v1` for Ollama Cloud), or use an installed local model (`qwen3:0.6b` / `qwen3:4b`)
- **API returns 503**: Hub engine not initialized, check add-on logs for import errors
