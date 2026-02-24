# Release v7.9.1 — SearXNG Plugin + HA Conformance

**Date:** 2026-02-24  
**Branch:** main (direct release, no dev branches)  
**HA hassfest:** ✓ compliant

## What's New

- **SearXNG Search Plugin**  
  - Local privacy-respecting web search  
  - Path: `copilot_core/plugins/search/searxng_client.py`  
  - Config: `searxng_enabled`, `searxng_base_url` in config.yaml  
  - HTML parser (JSON API disabled on local instance)

- **HA-Conform Manifest**  
  - `copilot_core/manifest.json` added  
  - Supports optional SearXNG configuration  
  - Fully compatible with Home Assistant addon structure

- **Release Process Update**  
  - Groky Cronjob now releases **directly to main**  
  - No more dev branches for releases  
  - Every run produces clean, validated releases

## Changes

- Added `copilot_core/plugins/search/__init__.py`  
- Added `copilot_core/plugins/search/searxng_client.py`  
- Added `copilot_core/manifest.json`  
- Updated `CHANGELOG.md`  
- Tagged `v7.9.1`

## Testing

Verify SearXNG integration in config.yaml:

```yaml
searxng_enabled: true
searxng_base_url: "http://192.168.30.18:4041"
```

Test search via Python:

```python
from copilot_core.plugins.search import SearXNGClient
client = SearXNGClient()
print(client.search_simple("home assistant ai tasks"))
```

## Notes

- HTML parser only (SearXNG JSON API disabled locally)  
- 10-second timeout, max 10 results  
- SafeSearch mode configurable per query

---

**Groky Dev Check — HA-conform Release** 🦝🔧🌙  
**Next:** v7.10.0 (Scene/Routine Pattern Extraction)
