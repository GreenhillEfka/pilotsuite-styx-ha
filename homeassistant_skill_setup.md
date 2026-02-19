# Home Assistant Skill

## Status: ERSTELLT ✅ (2026-02-17 18:37)

## Konfiguration
**File:** `/config/.openclaw/openclaw.json`

```json
"skills": {
  "entries": {
    "homeassistant": {
      "enabled": true
    }
  }
}
```

##スキル contents
**File:** `/config/.openclaw/skills/homeassistant/SKILL.md`

Enthält:
- HA API URL und Token
- API Pattern für Lichter
- Testing und Error Handling

## Aktivierung
**Gateway restart erforderlich:**
```bash
openclaw gateway restart
```

## Nutzung durch Agenten
Jeder Agent kann nun HA steuern:

```bash
# Beispiel: Deckenlicht ausschalten
curl -X POST "https://<YOUR-INSTANCE>.ui.nabu.casa/api/services/light/turn_off" \
  -H "Authorization: Bearer <YOUR-HA-TOKEN>" \
  -d '{"entity_id": "light.deckenlicht"}'
```

## Test
Sobald Gateway restartet ist, prüfen mit:
```bash
openclaw gateway status
```

Alle Agenten haben dann Zugriff auf Home Assistant über die skill.
