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
| Ollama URL | `http://localhost:11434` | Ollama server URL |
| Ollama Model | `qwen3:4b` | LLM model name |
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
- **LLM not responding**: Ollama needs 60s+ to start, check add-on logs
- **API returns 503**: Hub engine not initialized, check add-on logs for import errors
