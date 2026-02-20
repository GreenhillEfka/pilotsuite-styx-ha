# 🏠 PilotSuite - Einrichtungsanleitung

> **Version:** v0.9.3 | **Letzte Aktualisierung:** 15.02.2026

Diese Anleitung führt dich Schritt für Schritt durch die Installation und Konfiguration des PilotSuite für Home Assistant.

---

## 📋 Voraussetzungen

| Anforderung | Details |
|------------|---------|
| Home Assistant | Version 2023.10 oder höher |
| Hardware | Raspberry Pi 4+ / x86-64 / NAS |
| Speicher | Mindestens 2GB freier Speicher |
| Internet | Für Cloud-Modelle (optional) |

### Empfohlene Add-ons
- **Supervisor** (für HACS)
- **File Editor** (für Konfiguration)
- **Terminal & SSH** (für Debugging)

---

## 🚀 Schritt 1: HACS installieren

Falls du HACS noch nicht installiert hast:

1. **Home Assistant → Einstellungen → Add-ons**
2. **Add-on Store** (unten rechts) → ⋮ → **Repositories**
3. Folgende URL hinzufügen:
   ```
   https://github.com/hacs/integration
   ```
4. **HACS** installieren und starten
5. Home Assistant neu starten

---

## 🚀 Schritt 2: PilotSuite installieren

### Option A: Über HACS (empfohlen)

1. **Home Assistant → HACS**
2. **Integrations** → 🔍 nach "PilotSuite" suchen
3. **Herunterladen** → **Herunterladen** klicken
4. Home Assistant neu starten

### Option B: Manuell

```bash
cd /config/custom_components/
git clone https://github.com/GreenhillEfka/pilotsuite-styx-ha.git ai_home_copilot
```

---

## 🚀 Schritt 3: Integration hinzufügen

1. **Home Assistant → Einstellungen → Geräte & Dienste**
2. **Integration hinzufügen** (unten rechts)
3. Nach "PilotSuite" suchen
4. Klicken auf **PilotSuite**

---

## ⚙️ Schritt 4: Konfiguration

### Basis-Konfiguration

| Option | Beschreibung | Standard |
|--------|-------------|----------|
| **Core Add-on URL** | URL des Core Add-ons | `http://192.168.x.x:8909` |
| **API Token** | Authentifizierung | Wird automatisch generiert |
| **Log Level** | Detailgrad der Logs | `INFO` |

### Erweiterte Optionen

```yaml
# configuration.yaml (optional)
ai_home_copilot:
  core_url: "http://192.168.1.100:8909"
  log_level: DEBUG
  debug_mode: true
```

---

## 🎯 Schritt 5: Core Add-on installieren (optional)

Für erweiterte Features wie Brain Graph und Vector Store:

1. **Home Assistant → Einstellungen → Add-ons**
2. **Add-on Store** → ⋮ → **Repositories**
3. URL hinzufügen:
   ```
   https://github.com/GreenhillEfka/pilotsuite-styx-core
   ```
4. **Copilot Core** installieren
5. **Konfiguration:**
   ```yaml
   port: 8909
   log_level: info
   ```
6. **Starten**

---

## 📊 Schritt 6: Dashboard einrichten

### Lovelace Dashboard

1. **Home Assistant → Übersicht**
2. **⋮ → Dashboard bearbeiten**
3. **Karte hinzufügen** → **PilotSuite** auswählen

### Verfügbare Karten

| Karte | Beschreibung |
|-------|-------------|
| Brain Graph | Visuelle Darstellung des Wissensgraphen |
| Status | System-Status und Metriken |
| Energie | Energie-Insights und Empfehlungen |
| Automatisierungen | Predictive Automation Vorschläge |

---

## 🔧 Konfigurationseinstellungen

### Entity-Auswahl für Habitus Zones

1. **PilotSuite Integration** → **Konfigurieren**
2. **Zones auswählen** → Gewünschte Bereiche aktivieren
3. **Entities zuweisen** → Entities pro Zone auswählen

### ML-Features aktivieren

| Feature | Konfiguration |
|---------|--------------|
| **Predictive Automation** | In Automation Settings aktivieren |
| **Anomaly Detection** | Sensor konfigurieren |
| **Energy Insights** | Energie-Entities auswählen |
| **Habit Learning** | Tracking-Dauer festlegen |

---

## 🧪 Testen der Installation

### System-Status prüfen

1. **Entwicklerwerkzeuge → Zustände**
2. Nach `sensor.ai_home_copilot` suchen
3. Status sollte "Bereit" anzeigen

### API-Endpunkte testen

```bash
curl http://<CORE_URL>/api/v1/status
```

Erwartete Antwort:
```json
{
  "ok": true,
  "version": "0.6.1",
  "time": "2026-02-15T17:00:00Z"
}
```

---

## 🔧 Fehlerbehebung

### Problem: "Integration nicht gefunden"

**Lösung:**
1. Home Assistant neu starten
2. Cache leeren: Einstellungen → Speicher → Cache leeren

### Problem: "Core Add-on nicht erreichbar"

**Lösung:**
1. Add-on Logs prüfen
2. Firewall/Port prüfen (Port 8909)
3. IP-Adresse verifizieren

### Problem: "Keine Vorschläge"

**Lösung:**
1. Mindestens 7 Tage Daten sammeln
2. Zone-Entities korrekt konfigurieren
3. Log-Level auf DEBUG setzen

### Problem: "Import Fehler"

**Lösung:**
```bash
# Python-Pakete prüfen
pip3 install numpy scikit-learn
```

---

## 📈 Wartung

### Updates installieren

1. **HACS** → Updates verfügbar
2. **PilotSuite** → Update
3. Home Assistant neu starten

### Logs prüfen

```bash
# Core Add-on Logs
docker logs addons/local/a0_copilot_core

# HA Integration Logs
cat /config/home-assistant.log | grep ai_home_copilot
```

### Backup erstellen

Automatische Backups werden über die Safety-Buttons erstellt:
- `button.copilot_safety_backup_create`

---

## 🎉 Fertig!

Dein PilotSuite ist jetzt eingerichtet. 

**Nächste Schritte:**
1. 📊 Brain Graph im Dashboard ansehen
2. ⚡ Energy Insights konfigurieren
3. 🤖 Predictive Automations testen
4. 📱 Benachrichtigungen aktivieren

---

## 📞 Support

- **GitHub Issues:** https://github.com/GreenhillEfka/pilotsuite-styx-ha/issues
- **Dokumentation:** docs/ folder
- **Discord:** Community-Link in GitHub

---

*Made with ❤️ for Home Assistant*
