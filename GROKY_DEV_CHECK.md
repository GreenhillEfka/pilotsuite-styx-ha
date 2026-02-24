# Groky Dev Check Script

**Location:** `/config/.openclaw/workspace/groky_dev_check.py`  
**Run:** `*/10 * * * * python3 /config/.openclaw/workspace/groky_dev_check.py` (via crontab)

---

## Features

- **PHASE 1**: Repo Status (`git fetch`, `git log`, `git status`)
- **PHASE 2**: Bugfix Round (P0) — Error Isolation & Connection Pooling
- **PHASE 3**: Feature Extension (P1/P2) — SearXNG & Plugin System
- **PHASE 4**: HA Conformance — manifest.json, HACS structure
- **PHASE 5**: Release + Notes — CHANGELOG.md, RELEASE_NOTES.md, Git tag
- **PHASE 6**: Status Report — Telegram Report an Mensch
- **PHASE 7 (NEU!)**: System Integrity — Dashboard + Frontend/Backend API + UX stress test

---

## Model Chain

- Primary: `xai/grok-4`
- Fallback: `ollama/qwen3-coder-next:cloud`

---

## Ziel jedes Loops

- **Kernprobleme identifizieren** und lösungen implementieren  
- **Dashboard + Frontend/Backend-Kommunikation** validieren  
- **Konfiguration und Benutzererfahrung** von Grund auf optimieren  
- **System stabilisieren** und HA-conform release-fähig machen  

---

## WICHTIG

Jeder Loop = **SAUBERES RELEASE** (vX.Y.Z).  
Bei KEINEM Input → HEARTBEAT_OK.

---

## Cron Setup

```bash
crontab -e
*/10 * * * * python3 /config/.openclaw/workspace/groky_dev_check.py
```
