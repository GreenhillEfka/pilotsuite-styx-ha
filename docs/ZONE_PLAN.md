# Habitus Zones Plan

## Geplante Zones

| Zone | Typ | Entities (vorgeschlagen) |
|------|-----|-------------------------|
| Wohnbereich | area | Licht, Media, Sensoren |
| Kochbereich | area | Licht, Sensoren |
| Gangbereich | area | Licht, Sensoren |
| Badbereich | area | Licht, Sensoren |
| Schlafbereich | area | Licht, Media |
| Terrassenbereich | outdoor | Licht, Sensoren |

## Tag → Zone Mapping

Das Tag-System soll automatisch Entities den passenden Zones zuordnen:

```
aicp.place.wohnzimmer → Zone: Wohnbereich
aicp.place.kuche      → Zone: Kochbereich
aicp.place.gang       → Zone: Gangbereich
aicp.place.bad        → Zone: Badbereich
aicp.place.schlafzimmer → Zone: Schlafbereich
aicp.place.terrasse   → Zone: Terrassenbereich
```

## Dashboard Feature

Auf der Habitus Zones Dashboard-Seite:
1. Liste aller Zones anzeigen
2. Für jede Zone: "Entitäten vorschlagen" Button
3. Vorschlag basiert auf:
   - `aicp.place.X` Tags
   - Entity-Namen (enthält Zone-Namen)
   - HA Areas
4. User kann Vorschlag akzeptieren oder anpassen

## Implementierung

1. Zone-Definitions erweitern
2. Tag→Zone Mapping integrieren
3. Dashboard Card mit "Entity vorschlagen" Feature
4. User-Bestätigung vor Übernahme
