# AI Home CoPilot Audit Brief

## Ziel
Vereinigung von zwei Codebasen in die Architektur:
- **Add-on** (`addons/copilot_core/`) = Backend (Neurons, Brain Graph API, etc.)
- **Integration** (`custom_components/copilot/`) = Adapter (Entities, HA API)

## Zu analysieren
1. `ai_home_copilot_hacs_repo/custom_components/ai_home_copilot/` (269 .py)
2. `addons/copilot_core/rootfs/usr/src/app/copilot_core/` (180 .py)
3. `custom_components/copilot/` (Stub - nur __init__.py)

## Fragen
1. Welche Features existieren NUR in hacs_repo? (müssen migriert werden)
2. Welche Features existieren NUR im Add-on? (sind OK)
3. Welche Features existieren in BEIDEN? (konflikte?)
4. Welche Ports/APIs werden verwendet? (Inkonsistenzen?)
5. Was ist der empfohlene Merge-Pfad?

## Dateien
- Integration hacs: ai_home_copilot_hacs_repo/custom_components/ai_home_copilot/
- Add-on: addons/copilot_core/rootfs/usr/src/app/copilot_core/
- Integration stub: custom_components/copilot/
