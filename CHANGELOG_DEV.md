# CHANGELOG_DEV

Dev-only changelog for WIP module kernel work. Not shipped to users.

## 2026-02-09

### brain_graph (v0.1 kernel)
- Added `brain_graph_entities.py`: two sensors (`brain graph nodes`, `brain graph edges`) exposing live graph size via Core API.
- Registered sensors in `sensor.py` async_setup_entry.
- Existing: `brain_graph_viz.py` button for HTML/SVG publish (already on `development`).
- Privacy: sensors expose only aggregate counts, no raw node/edge data.
