# Release v7.10.0 — Plugin System v1 + SearXNG

**Date:** 2026-02-24  
**Branch:** main (direct release, no dev branches)  
**Tag:** `v7.10.0`  
**HA hassfest:** ✓ compliant (addon structure, manifest.json)

## What's New

- **Plugin System v1**  
  - Base classes: `PluginBase`, `PluginManager`  
  - New plugins can be added via `/copilot_core/plugins/`  
  - Every plugin has `PLUGIN_ID`, config schema, `execute()`, `get_status()`

- **Search Plugin**  
  - Local SearXNG web search (HTML parser, no JSON API)  
  - Config: `enabled`, `base_url`, `timeout`, `max_results`, `safesearch`, `default_language`

- **LLM Plugin**  
  - Local (Ollama) / Cloud (OpenAI-compatible) switching  
  - Config: `ollama_url`, `ollama_model`, `cloud_api_url`, `cloud_model`, `prefer_local`, `assistant_name`

- **React Backend API**  
  - `/api/plugins` — list all plugins  
  - `/api/plugins/{id}/enable` — enable plugin  
  - `/api/plugins/{id}/disable` — disable plugin  
  - `/api/plugins/{id}/execute` — execute with args  
  - `/api/plugins/{id}/config` — update config (PUT)

## Files Changed

- `copilot_core/plugins/__init__.py` — module exports  
- `copilot_core/plugins/plugin_base.py` — base classes  
- `copilot_core/plugins/search_plugin.py` — SearXNG plugin  
- `copilot_core/plugins/llm_plugin.py` — LLM plugin  
- `copilot_core/plugins/react_backend.py` — web UI controller  
- `copilot_core/plugins/search/__init__.py` — search client wrapper  
- `copilot_core/manifest.json` — added `searxng_enabled`, `searxng_base_url`  
- `CHANGELOG.md`, `RELEASE_NOTES.md`, `plugins/README.md`

## Configuration (config.yaml)

```yaml
plugins:
  llm:
    enabled: true
    ollama_url: "http://localhost:11435"
    ollama_model: "qwen3:0.6b"
    cloud_api_url: "https://ollama.com/v1"
    cloud_api_key: ""
    cloud_model: "gpt-oss:20b"
    prefer_local: true
    assistant_name: "Styx"

  search:
    enabled: true
    base_url: "http://192.168.30.18:4041"
    timeout: 10
    max_results: 10
    safesearch: 0
    default_language: "auto"
```

## Usage Example (Python)

```python
from copilot_core.plugins import PluginManager, SearchPlugin, LLMPlugin

# Init manager
manager = PluginManager()
manager.register(SearchPlugin({"enabled": True, "base_url": "http://192.168.30.18:4041"}))
manager.register(LLMPlugin({"enabled": True, "ollama_url": "http://localhost:11435", "assistant_name": "Styx"}))

# Execute search
results = manager.execute("search", "home assistant ai tasks")
print(results)

# Get status
print(manager.get_status())
```

## Usage Example (Web UI)

React frontend can call:

```bash
GET /api/plugins
POST /api/plugins/search/enable
POST /api/plugins/search/disable
POST /api/plugins/search/execute?query=home+assistant
PUT /api/plugins/search/config --data '{"base_url":"http://192.168.30.18:4041"}'
```

## Upgrade Notes

- Existing plugins remain unchanged  
- New plugins are opt-in via `enabled: true` in config  
- SearXNG plugin is optional — falls back gracefully if disabled

---

**Groky Dev Check — HA-conform Release** 🦝🔧🌙  
**Next:** SearXNG in `llm_provider.py` integration for auto-searching
