# Zone Detection

## Overview

The Zone Detection module provides automatic zone recognition based on device_tracker and person entities in Home Assistant.

## Features

- **Automatic Zone Detection**: Detects zones based on presence (person/device_tracker)
- **Zone Templates**: Pre-configured zone patterns (home, work, away, shared, sleep)
- **Multi-User Clustering**: Detects when multiple users are in the same zone ("zusammen sein")
- **Time-based Detection**: Supports time-based zone patterns (e.g., sleep mode)

## Zone Templates

### home
Standard home zone - detected when any person entity is "home"

### work
Work zone - typically location-based or manually configured

### away
Away zone - detected when NO person entities are "home"

### shared
Shared zone - detected when MULTIPLE users are "home" (minimum 2)

### sleep
Sleep zone - time-based detection (default: 22:00-08:00)

## Usage

### Python API

```python
from ai_home_copilot.zone_detector import ZoneDetector, DetectedZone

# Initialize
detector = ZoneDetector(hass, config_entry)

# Set up
await detector.async_setup()

# Get user zone
zone = detector.get_user_zone("person.efka")
print(f"User in zone: {zone.zone_name}")

# Check if users are together
is_together = detector.is_together(["person.efka", "person.partner"])

# Get zone summary
summary = detector.get_zone_summary()
```

## Lovelace Cards

The dashboard_cards module provides several Lovelace UI cards:

- `energy_distribution_card.py` - Energy consumption visualization
- `media_context_card.py` - Media playback context
- `zone_context_card.py` - Zone occupancy status
- `user_together_card.py` - Multi-user clustering

## API Endpoints

### GET /api/v1/zone/detect
Detect zone for a specific person entity

### GET /api/v1/zone/list
List all detected zones

### GET /api/v1/zone/together
Get users in the same zone

### GET /api/v1/zone/templates
Get available zone templates