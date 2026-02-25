# PilotSuite Installation (HA Integration)

Stand: **v8.9.1**

## Schnellpfad

1. Core Add-on Repo hinzufügen: `https://github.com/GreenhillEfka/pilotsuite-styx-core`
2. Core starten und `http://<HA-IP>:8909/health` prüfen
3. HACS Repo hinzufügen: `https://github.com/GreenhillEfka/pilotsuite-styx-ha` (Integration)
4. Integration installieren, Home Assistant neu starten
5. Integration `PilotSuite - Styx` hinzufügen (Zero Config)

## Manuelle Verbindungswerte

- Host: HA-Host oder Core-Host
- Port: `8909`
- Token: optional, aber bei gesetztem Core-Token identisch setzen

## Validierung

- `binary_sensor.ai_home_copilot_online` = `on`
- `sensor.ai_home_copilot_version` vorhanden
- Core API erreichbar:

```bash
curl -sS http://<HA-IP>:8909/health
curl -sS http://<HA-IP>:8909/chat/status
```

## Nach Update

- Wenn HACS `Restart required` anzeigt: Home Assistant neu starten.
- Ab `v8.9.1` werden alte Low-Signal-Seed-Reparaturmeldungen beim Setup automatisch entfernt.

## Referenz

Detailanleitung: `SETUP.md`
