# Changelog

All notable changes to AI Home CoPilot will be documented in this file.

## [0.8.15] - 2026-02-15

### Added
- **Suggestion Panel** (`suggestion_panel.py`): Dedicated UI for AI Home CoPilot suggestions
  - Timeline view of pending suggestions
  - Accept/Reject/Snooze actions via service calls
  - Confidence indicator and "Why?" explanations
  - Zone and Mood context display
  - Priority-based sorting (High/Medium/Low)
  - WebSocket API for real-time updates

- **Mood Dashboard** (`mood_dashboard.py`): Visualisierung der aktuellen Stimmung
  - MoodSensor with icon, color, and German name
  - MoodHistorySensor for tracking mood changes
  - MoodExplanationSensor with "Warum?" explanations
  - Lovelace card config generator
  - Top contributing factors display

- **Calendar Context Neuron** (`calendar_context.py`): Kalender-basierter Kontext
  - Meeting detection (now/soon)
  - Weekend/holiday detection
  - Vacation mode detection
  - Mood weight computation based on calendar events
  - Conflict detection
  - Keyword-based categorization (focus, social, relax, alert)

### Enhanced
- Extended `const.py` with new configuration options
- Added sensor entities: ZoneOccupancySensor, UserPresenceSensor, UserPreferenceSensor, SuggestionQueueSensor
- Added calendar context integration to sensor setup

### Technical
- All modules pass py_compile validation
- WebSocket API with proper error handling
- Async storage for suggestion persistence

## [0.8.14] - 2026-02-15

### Added
- Enhanced Repairs UX with zone and mood context
- Risk visualization for suggestions

## [0.8.0] - 2026-02-15

### Added
- Multi-User Preference Learning (MUPL) v0.8.0
- User-spezifische Mood-Gewichtung
- Debug Mode v0.8.0

## [0.4.33] - 2026-02-14

### Added
- Neuronen-System: Context, State, Mood, Weather, Presence, Energy, Camera
- Habitus Zones: Zone-basierte Muster-Erkennung
- Tag System v0.2
- Brain Graph