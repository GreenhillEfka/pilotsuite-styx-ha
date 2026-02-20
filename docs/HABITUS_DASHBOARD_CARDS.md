# Habitus Dashboard Cards

Dieses Dokument beschreibt die neuen Lovelace Dashboard Cards für die Habitus-Zonen-Integration.

## Übersicht

Die Habitus Dashboard Cards bieten visuelle Darstellungen für:

1. **Zone Status Card** - Aktuelle Zone und Score
2. **Zone Transitions Card** - History der Zone-Änderungen
3. **Mood Distribution Card** - Aktuelle Stimmungsverteilung

## Verfügbare Cards

### 1. Zone Status Card

Zeigt die aktuell aktive Zone, den Zone-Score (0-100%) und optional die erkannte Stimmung.

```yaml
# Einfache Version (standalone)
type: custom:vertical-stack
cards:
  - type: markdown
    title: Habitus Zone
    content: |
      **Aktiv:** Wohnzimmer
      
  - type: gauge
    entity: sensor.ai_home_copilot_zone_score
    title: Zone Score
    min: 0
    max: 100
    severity:
      green: 70
      yellow: 40
      red: 20
```

#### Entitäten für Zone Status

| Entität | Beschreibung |
|---------|--------------|
| `sensor.ai_home_copilot_habitus_zone_status` | Aktive Zone (Name) |
| `sensor.ai_home_copilot_zone_<zone_id>_score` | Score pro Zone (0-100%) |
| `sensor.ai_home_copilot_habitus_current_mood` | Aktuelle Gesamtstimmung |

### 2. Zone Transitions Card

Zeigt die History der Zone-Änderungen mit Zeitstempel, Auslöser und optionalem Confidence-Wert.

```yaml
type: custom:vertical-stack
cards:
  - type: markdown
    title: Zone Transitions
    content: |
      **Letzte Zone-Änderungen:**
      
      - *10:00:00*: Küche → Wohnzimmer (motion)
      - *09:30:00*: unbekannt → Küche (time)
      
  - type: history-graph
    title: Zone-Historie
    hours_to_show: 24
    entities:
      - sensor.ai_home_copilot_zone_wohnzimmer
      - sensor.ai_home_copilot_zone_kueche
```

#### Entitäten für Transitions

| Entität | Beschreibung |
|---------|--------------|
| `sensor.ai_home_copilot_habitus_transitions` | JSON-Array mit allen Übergängen |

### 3. Mood Distribution Card

Zeigt die Verteilung der Stimmungen über alle Zonen.

```yaml
type: custom:vertical-stack
cards:
  - type: markdown
    title: Stimmungsverteilung
    content: |
      - **Wohnzimmer:** relax (60%)
      - **Büro:** focus (40%)
      
  - type: grid
    columns: 2
    cards:
      - type: custom:bar-card
        entity: sensor.ai_home_copilot_mood_wohnzimmer
        title: Wohnzimmer
        min: 0
        max: 100
      - type: custom:bar-card
        entity: sensor.ai_home_copilot_mood_buero
        title: Büro
        min: 0
        max: 100
```

#### Entitäten für Mood

| Entität | Beschreibung |
|---------|--------------|
| `sensor.ai_home_copilot_habitus_mood_distribution` | JSON mit Mood-Verteilung |
| `sensor.ai_home_copilot_habitus_current_mood` | Aktuelle Gesamtstimmung |

## Komplettes Dashboard-Beispiel

```yaml
title: PilotSuite - Habitus
views:
  - title: Habitus Zonen
    icon: mdi:home-circle
    cards:
      # Row 1: Zone Status
      - type: custom:vertical-stack
        cards:
          - type: markdown
            title: Aktueller Status
            content: |
              **Aktive Zone:** Wohnzimmer
              **Score:** 75%
              
          - type: entities
            title: Zonen
            entities:
              - entity: sensor.ai_home_copilot_zone_wohnzimmer_score
                name: Wohnzimmer
              - entity: sensor.ai_home_copilot_zone_kueche_score
                name: Küche
              - entity: sensor.ai_home_copilot_zone_schlafzimmer_score
                name: Schlafzimmer
      
      # Row 2: Mood Distribution
      - type: custom:vertical-stack
        cards:
          - type: markdown
            title: Mood Verteilung
            content: |
              **Verteilung:**
              - relax: 3 Zonen (60%)
              - focus: 2 Zonen (40%)
              
          - type: gauge
            entity: sensor.ai_home_copilot_habitus_current_mood
            title: Aktuelle Stimmung
```

## Automatische YAML-Generierung

Die Integration bietet einen vorkonfigurierten YAML-Text, der alle Card-Konfigurationen enthält:

1. Gehe zu **Entwicklerwerkzeuge** → **Zustände**
2. Suche nach `text.ai_home_copilot_habitus_cards_yaml`
3. Kopiere den YAML-Inhalt in dein Lovelace Dashboard

## Konfiguration

### Zone-Score-Berechnung

Der Zone-Score wird basierend auf der Anzahl aktiver Entitäten berechnet:

```
Score = (Aktive Entitäten / Gesamte Entitäten) × 100
```

Aktiv bedeutet: State ist nicht `off`, `unavailable` oder `unknown`.

### Mood-Erkennung

Die Mood-Erkennung erfolgt basierend auf dem Zone-Score:

| Score | Mood |
|-------|------|
| > 80 | energy |
| > 50 | focus |
| > 20 | relax |
| ≤ 20 | sleep |

**Hinweis:** In einer vollständigen Implementation würde die Mood-Erkennung durch das Core Add-on erfolgen.

## Bekannte Einschränkungen

1. **Bar-Card**: Erfordert `custom:bar-card` Lovelace-Erweiterung
2. **Mood-Distribution**: Zeigt nur aggregierte Daten, keine Zeitverläufe
3. **Transitions**: Speichert nur die letzten 20 Übergänge in der Entität
4. **Echtzeit-Updates**: Änderungen erfordern einen Browser-Refresh
5. **Unicode**:alle Funktionen unterstützen Unicode-Zeichen

## Nächste Schritte

1. **Core API Integration**: Mood-Erkennung vom Core Add-on übernehmen
2. **Echtzeit-Updates**: WebSocket-Support für Live-Updates
3. **Weitere Cards**: 
   - Energy Distribution Card
   - Media Context Card
   - Weather/PV Card
4. **Mobile-Optimierung**: Separate Layouts für mobile Ansichten
5. **Themes**: Unterstützung für Light/Dark Themes

## Dateien

| Datei | Beschreibung |
|-------|--------------|
| `habitus_dashboard_cards.py` | YAML-Generatoren für Cards |
| `habitus_dashboard_entities.py` | Sensor-Entitäten für Cards |
| `tests/test_habitus_dashboard_cards.py` | Unit Tests |

## Siehe auch

- [Habitus Zonen](./HABITUS_ZONES.md)
- [Dashboard Lovelace](./DASHBOARD_LOVELACE.md)
- [Operations](./OPERATIONS.md)
