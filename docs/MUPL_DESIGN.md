# Multi-User Preference Learning (MUPL) v0.8.0

> **Design Document** - 2026-02-15
> Branch: `dev/mupl-v0.8.0`

---

## 1. Ziel

Erkenne verschiedene Nutzer im Haushalt und lerne deren individuelle Präferenzen:
- Wer ist zu Hause? (Presence Detection)
- Wer interagiert mit welchen Geräten? (Action Attribution)
- Was sind die bevorzugten Einstellungen pro Person? (Preference Profile)

---

## 2. Architektur

### 2.1 Komponenten

```
┌─────────────────────────────────────────────────────────────┐
│                    HA Integration                            │
│  ┌─────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │ UserDetector│  │ PreferenceStore  │  │ UserMoodEntity │ │
│  └──────┬──────┘  └────────┬─────────┘  └───────┬────────┘ │
│         │                  │                     │          │
│         └──────────────────┼─────────────────────┘          │
│                            │                                │
│  ┌─────────────────────────▼─────────────────────────────┐ │
│  │              MultiUserPreferenceModule                 │ │
│  │  - user_detection: Wer ist zu Hause?                  │ │
│  │  - action_attribution: Wer hat was gemacht?           │ │
│  │  - preference_learning: Was mag wer?                  │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Datenmodell

```python
# Preference Store (JSON in .storage/ai_home_copilot_preferences)
{
  "users": {
    "person.efka": {
      "name": "Efka",
      "preferences": {
        "light_brightness": {
          "default": 0.8,
          "by_zone": {
            "wohnzimmer": 0.7,
            "schlafzimmer": 0.3
          }
        },
        "media_volume": {
          "default": 0.5,
          "by_zone": {}
        },
        "temperature": {
          "default": 21.0,
          "by_zone": {
            "schlafzimmer": 19.0
          }
        },
        "mood_weights": {
          "comfort": 0.7,
          "frugality": 0.4,
          "joy": 0.6
        }
      },
      "patterns": {
        "evening_routine": {
          "trigger_time": "22:00",
          "actions": ["light.schlafzimmer_dim", "media_volume_low"]
        }
      },
      "last_seen": "2026-02-15T04:00:00+01:00",
      "interaction_count": 1250
    }
  },
  "device_affinities": {
    "media_player.wohnzimmer": {
      "primary_user": "person.efka",
      "usage_distribution": {
        "person.efka": 0.85,
        "person.partner": 0.15
      }
    }
  }
}
```

---

## 3. Implementation

### 3.1 User Detection (Phase 1)

**Quellen (priorisiert):**
1. `person.*` entities (Home Assistant Person Integration)
2. `device_tracker.*` mit `source_type=gps` oder `bluetooth`
3. `input_boolean.*` Manuel Presence Toggle
4. `binary_sensor.*` Motion + Device Correlation

**Algorithmus:**
```python
async def detect_active_users(self) -> list[str]:
    """Erkenne anwesende und aktive Nutzer."""
    active_users = []
    
    for person_entity in self._person_entities:
        state = self.hass.states.get(person_entity)
        if state and state.state == "home":
            active_users.append(person_entity)
    
    return active_users
```

### 3.2 Action Attribution (Phase 2)

**Quellen:**
1. Service Call Context (`context.user_id`)
2. Device Affinity (historische Nutzung)
3. Proximity (Wer ist im Raum?)
4. Time-based Heuristic (Wer ist typischerweise zu dieser Zeit aktiv?)

**Konfidenz-Level:**
- `high`: User ID im Service Call Context
- `medium`: Device Affinity > 0.8
- `low`: Proximity + Time Heuristic

### 3.3 Preference Learning (Phase 3)

**Lern-Mechanismus:**
```python
async def learn_from_action(self, user_id: str, action: Action):
    """Lerne Präferenz aus einer Aktion."""
    # Brightness
    if action.domain == "light" and "brightness" in action.data:
        await self._update_brightness_preference(
            user_id, 
            action.entity_id, 
            action.data["brightness"]
        )
    
    # Temperature
    if action.domain == "climate" and "temperature" in action.data:
        await self._update_temperature_preference(
            user_id,
            action.entity_id,
            action.data["temperature"]
        )
    
    # Media Volume
    if action.domain == "media_player" and "volume_level" in action.data:
        await self._update_volume_preference(
            user_id,
            action.entity_id,
            action.data["volume_level"]
        )
```

**Exponential Smoothing:**
```python
def update_preference(current: float, new_value: float, alpha: float = 0.3) -> float:
    """Glätte Präferenz-Updates."""
    return current * (1 - alpha) + new_value * alpha
```

---

## 4. Integration mit Mood Context

### 4.1 User-Spezifischer Mood

```python
class UserMoodEntity(SensorEntity):
    """Mood pro Nutzer, nicht global."""
    
    _attr_name = "AI CoPilot User Mood"
    
    def __init__(self, user_id: str):
        self._user_id = user_id
        self._mood = {
            "comfort": 0.5,
            "frugality": 0.5,
            "joy": 0.5
        }
    
    async def async_update(self):
        # Hole User Preferences
        prefs = await self._get_user_preferences(self._user_id)
        
        # Mood basierend auf Preferences gewichten
        self._mood = prefs.get("mood_weights", self._mood)
```

### 4.2 Multi-User Mood Aggregation

Bei mehreren aktiven Nutzern:
- **Konsens-Modus**: Gemeinsame Präferenzen bevorzugen
- **Priority-Modus**: Bestimmter User hat Vorrang
- **Konflikt-Erkennung**: Warnung bei widersprüchlichen Präferenzen

```python
def aggregate_moods(user_moods: dict[str, Mood]) -> Mood:
    """Aggregiere Mood mehrerer Nutzer."""
    if len(user_moods) == 1:
        return list(user_moods.values())[0]
    
    # Gewichtete Aggregation basierend auf User Priority
    total_weight = 0
    aggregated = Mood()
    
    for user_id, mood in user_moods.items():
        weight = get_user_priority(user_id)
        aggregated.comfort += mood.comfort * weight
        aggregated.frugality += mood.frugality * weight
        aggregated.joy += mood.joy * weight
        total_weight += weight
    
    return aggregated / total_weight
```

---

## 5. API Endpoints

### 5.1 REST API

```
GET  /api/v1/users                    # Liste erkannte Nutzer
GET  /api/v1/users/{user_id}          # User-Profil
POST /api/v1/users/{user_id}/learn    # Explizit Präferenz setzen
GET  /api/v1/users/{user_id}/mood     # User-spezifischer Mood
POST /api/v1/users/{user_id}/mood     # Mood updaten
```

### 5.2 Services

```yaml
# services.yaml
learn_preference:
  name: Learn Preference
  description: Lerne eine Präferenz für einen User
  fields:
    user_id:
      description: User ID (person.entity_id)
      example: "person.efka"
    preference_type:
      description: Art der Präferenz
      example: "light_brightness"
    value:
      description: Präferenz-Wert
      example: 0.8
    zone:
      description: Optional: Zone-spezifische Präferenz
      example: "wohnzimmer"

set_user_priority:
  name: Set User Priority
  description: Setze Priorität für Multi-User Konflikte
  fields:
    user_id:
      description: User ID
    priority:
      description: Priorität (0.0-1.0)
```

---

## 6. Entities

```yaml
# Neue Entities
sensor.ai_copilot_active_users:
  name: "Aktive Nutzer"
  icon: mdi:account-group
  state: count
  attrs:
    - users: ["person.efka", "person.partner"]

sensor.ai_copilot_user_mood_efka:
  name: "Mood - Efka"
  icon: mdi:robot-happy
  state: mood_name
  attrs:
    - comfort: 0.7
    - frugality: 0.4
    - joy: 0.6

sensor.ai_copilot_user_mood_partner:
  name: "Mood - Partner"
  icon: mdi:robot-happy
  state: mood_name
  attrs:
    - comfort: 0.5
    - frugality: 0.6
    - joy: 0.4
```

---

## 7. Privacy

### 7.1 Privacy-First Prinzipien

1. **Lokal**: Alle Daten bleiben lokal in HA Storage
2. **Opt-in**: User muss aktiviert werden
3. **Transparent**: User kann alle Daten einsehen
4. **Löschbar**: User kann eigene Daten löschen

### 7.2 Daten-Retention

```python
# Config
PREFERENCE_RETENTION_DAYS = 90
PATTERN_RETENTION_DAYS = 30
ANONYMIZE_AFTER_DAYS = 180
```

---

## 8. Migration

### 8.1 Von Single-User

```python
async def migrate_single_user_prefs():
    """Migriere existierende globale Präferenzen zu User-spezifisch."""
    global_prefs = await get_global_preferences()
    primary_user = await get_primary_user()
    
    if primary_user and global_prefs:
        await set_user_preferences(primary_user, global_prefs)
        await mark_migration_complete("v0.8.0_mupl")
```

---

## 9. Testing

### 9.1 Test-Szenarien

1. **Single User Detection**: Ein User zu Hause
2. **Multi User Detection**: Mehrere Users zu Hause
3. **Action Attribution**: Service Call mit User Context
4. **Preference Learning**: Brightness Update → Preference gespeichert
5. **Mood Aggregation**: Zwei Users mit konkurrierenden Moods
6. **Privacy**: User Daten löschen

---

## 10. Release-Plan

| Phase | Version | Scope |
|-------|---------|-------|
| **Phase 1** | v0.8.0 | User Detection + Preference Storage |
| **Phase 2** | v0.8.1 | Action Attribution + Learning |
| **Phase 3** | v0.8.2 | Multi-User Mood + Aggregation |
| **Phase 4** | v0.8.3 | UI Integration + Services |

---

## 11. Abhängigkeiten

- **Mood Context Module** (v0.5.7): User Mood baut darauf auf
- **Habitus Zones v2** (v0.4.15): Zone-basierte Präferenzen
- **Tag System v0.2** (v0.4.14): Entity-Klassifizierung für Affinitäten

---

*Dieses Dokument wird während der Implementierung aktualisiert.*