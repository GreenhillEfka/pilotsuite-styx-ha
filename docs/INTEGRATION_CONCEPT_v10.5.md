# PilotSuite v10.5 — Integrationskonzept "SmartHome Andreas"

> Erstellt am 2026-02-27 auf Basis der Live-HA-Instanz (homeassistant.local:8123)
> HA Version: 2026.2.3 | 4520 Entities | 47 Areas | 7 Personen | 99 aktive Automationen

---

## 1. SmartHome-Gesamtbild

### 1.1 Hausuebersicht

```
                    ┌─────────────────────────────────────────┐
                    │              DACHGESCHOSS                │
                    │  ┌──────────┐  ┌───────────────────┐    │
                    │  │ Zimmer   │  │      Loft          │    │
                    │  │  Paul    │  │  (Sony, Flutlicht) │    │
                    │  └──────────┘  └───────────────────┘    │
                    ├─────────────────────────────────────────┤
                    │              ERDGESCHOSS                 │
  ┌────────┐  ┌────┤                                          │
  │Terrasse│──│ WZ │  Wohnzimmer (Hauptraum)                  │
  │ Garten │  │    │  FP2, 2x Thermostat, Sonos, TV, Xbox    │
  └────────┘  └──┬─┤                                          │
                 │  │  ┌──────┐ ┌──────┐ ┌─────────────┐     │
                 │  │  │ Gang │ │Kueche│ │Arbeitszimmer│     │
                 │  │  │Kaffee│ │Robots│ │Xbox,Sonos,  │     │
                 │  │  │Sonos │ │Sonos │ │LaMetric,FP1 │     │
                 │  │  └──┬───┘ └──────┘ └─────────────┘     │
                 │  │     │                                    │
                 │  │  ┌──┴──┐ ┌──────┐ ┌─────────┐          │
                 │  │  │ Bad │ │Toilet│ │Schlaf-  │          │
                 │  │  │Hue  │ │Wasch.│ │zimmer   │          │
                 │  │  │Sonos│ │Dufti │ │Sonos,   │          │
                 │  │  └─────┘ └──────┘ │Wecker   │          │
                 │  │                    └─────────┘          │
  ┌──────────┐  │  │  ┌────────────┐ ┌───────────┐           │
  │Vorder-   │──┤  │  │Kinderzimmer│ │ Speise-   │           │
  │eingang   │  │  │  │  Mira      │ │ kammer    │           │
  └──────────┘  │  │  └────────────┘ └───────────┘           │
                └──┤                                          │
                   │  ┌───────┐ ┌──────────┐ ┌────────┐      │
                   │  │Vorraum│ │Erdkeller  │ │Werkst. │     │
                   │  └───────┘ └──────────┘ └────────┘      │
                   └──────────────────────────────────────────┘
```

### 1.2 Bewohner

| Person   | Status  | Rolle       | Devices              |
|----------|---------|-------------|----------------------|
| Andreas  | home    | Admin/Owner | iPhone, iPad, MacBook Air, M2 Pro |
| Efka     | home    | Bewohner    | -                    |
| Steffi   | unknown | Bewohner    | -                    |
| Gustav   | unknown | Bewohner    | -                    |
| Katharina| unknown | Bewohner    | -                    |
| Mira     | unknown | Kind        | (Alexa Zimmer Mira)  |
| Pauli    | unknown | Kind        | -                    |

### 1.3 Infrastruktur

| System             | Details                                        |
|--------------------|------------------------------------------------|
| **Netzwerk**       | UniFi Dream Machine SE, USW-Lite-8-PoE, USW-Flex-Mini, U6 Mesh |
| **NAS**            | Synology DS1515 + DX517 (10 Drives, Disk 3 crashed!, Vol 4 @ 90.4%) |
| **Heizung**        | Wolf CGB-2 Gasheizung, 322K Brennerstarts, 22596h Laufzeit |
| **Solar/PV**       | Kaco Powador 12000, Ost+West Ausrichtung (~38 kWh/Tag) |
| **Energie**        | Stromverbrauch Paradiesgarten 3-Phasen (891W aktuell, 803W Produktion) |
| **Protokolle**     | Z-Wave (800 Series), Zigbee (Zigbee2MQTT), Hue (Bridge Pro), WiFi, Netatmo |
| **Smart Speaker**  | Sonos (6 Zonen), Alexa (7 Geraete), Apple Siri (1) |
| **Kameras**        | AI360, Netatmo Welcome, Netatmo Presence, Aqara G5 Pro, Doorbell |
| **Voice**          | HA Voice (Arbeitszimmer, Wohnzimmer), Piper+Whisper+OpenWakeWord |
| **AI**             | Perplexity AI (sonar-reasoning-pro), OpenAI (GPT-5.2, derzeit Fehler) |

### 1.4 Besonderheiten

- **Kaffeemaschine-Ecosystem**: 15.297 Bezuege, 5.796 Einschaltvorgaenge, taegl. Reset, TTS-Benachrichtigung
- **Waschmaschine**: LG ThinQ mit detailliertem Status (Lauf, Trommelreinigung, Fehler)
- **Toiletten-Tracking**: Whizz-Count (4045), Shizz-Count (3048) — humorvoller Gesundheitsindikator
- **Sonnenwecker**: Lichtwecker mit Sonnenaufgang-Simulation + Musik
- **Raumausleuchtung**: Pro Raum kalkulierte Ausleuchtung (Lux-basiert)
- **Sonos Autoplay**: Jede Zone hat eigenen Autoplay-Selector + SoundCloud Base
- **Presence per Room**: Eigene Anwesenheits-Boolean + Automation pro Raum

---

## 2. Habitus-Zonen-Mapping

### 2.1 Primaere Zonen (Neural Pipeline)

Jede Zone bekommt eine vollstaendige Neuron-Kette: Context → State → Mood

```
┌─────────────────┬──────────┬──────────┬─────────────────────────┐
│ Habitus-Zone    │ Raeume   │ Prioritaet│ Hauptfunktion           │
├─────────────────┼──────────┼──────────┼─────────────────────────┤
│ zone:wohnbereich│ Wohnzimmer│ 9        │ Familien-Aufenthalt     │
│ zone:schlafber. │ Schlafzim.│ 8        │ Schlaf & Erholung       │
│ zone:kochbereich│ Kueche,  │ 7        │ Kochen & Versorgung     │
│                 │ Speisek. │          │                         │
│ zone:badbereich │ Bad,     │ 6        │ Hygiene & Gesundheit    │
│                 │ Toilette │          │                         │
│ zone:buero      │ Arbeitszm│ 8        │ Arbeit & Gaming         │
│ zone:gangbereich│ Gang,    │ 4        │ Durchgang & Kaffee      │
│                 │ Vorraum, │          │                         │
│                 │ Flur     │          │                         │
│ zone:kinder     │ Zimmer   │ 7        │ Kinder-Bereiche         │
│                 │ Mira,    │          │                         │
│                 │ Zimmer   │          │                         │
│                 │ Paul     │          │                         │
│ zone:loft       │ Loft     │ 3        │ Freizeit & Gaeste       │
│ zone:aussen     │ Terrasse,│ 2        │ Outdoor & Wetter        │
│                 │ Garten   │          │                         │
└─────────────────┴──────────┴──────────┴─────────────────────────┘
```

### 2.2 Infrastruktur-Zonen (kein Mood, nur Monitoring)

```
zone:infrastruktur  → Kontrollraum, Serverraum (System Health)
zone:energie        → PV, Gas, Strom (Energy Neuron)
zone:netzwerk       → UniFi, NAS (Network Neuron)
zone:sicherheit     → Kameras, Alarmanlagen, Tuersensoren
```

---

## 3. Entity-Mapping pro Zone

### 3.1 zone:wohnbereich

**Context-Entities (Sensoren → Neuron-Inputs)**

| Rolle        | Entity ID                                          | Aktuell    |
|--------------|----------------------------------------------------|------------|
| temperature  | sensor.thermostat_wohnzimmer_rechts_temperatur     | 22.43°C    |
| temperature  | sensor.thermostat_wohnzimmer_links_temperatur      | 23.32°C    |
| temperature  | sensor.temperatur_wohnbereich_messstation           | 24.1°C     |
| humidity     | sensor.thermostat_wohnzimmer_rechts_luftfeuchtigkeit| 26.6%     |
| humidity     | sensor.luftfeuchtigkeit_wohnbereich_messstation     | 42%        |
| co2          | sensor.co2_wohnbereich_messstation                  | 721 ppm    |
| noise        | sensor.larm_wohnbereich_messstation                 | 62 dB      |
| pressure     | sensor.luftdruck_wohnbereich_messstation             | 1018.1 hPa|
| brightness   | sensor.helligkeit_wohnzimmer                        | 13 lux     |
| motion       | binary_sensor.bewegung_wohnzimmer                   | on         |
| motion       | binary_sensor.bewegung_grosse_couch                 | off        |
| motion       | binary_sensor.bewegung_kleine_couch                 | off        |
| motion       | binary_sensor.bewegung_spielwiese                   | off        |
| motion       | binary_sensor.bewegung_schnapsschrank               | off        |
| motion       | binary_sensor.bewegung_durchgangsbereich_wohnbereich| on         |
| presence     | binary_sensor.wohnzimmer_anwesenheit                | on         |
| energy       | sensor.steckerleiste_wohnzimmer_electric_consumption_w | 2.6W    |
| energy       | sensor.steckerleiste_wohnzimmer_electric_consumption_w_2| 156.7W |

**State-Entities (Steuerbare Geraete)**

| Rolle    | Entity ID                                  | Aktuell    |
|----------|--------------------------------------------|------------|
| lights   | light.beleuchtung_wohnzimmer               | on         |
| lights   | light.deckenlicht                          | on         |
| lights   | light.beleuchtung_durchgangsbereich        | on         |
| lights   | light.beleuchtung_terrassentur             | on         |
| heating  | climate.thermostat_wohnzimmer_rechts       | heat       |
| heating  | climate.thermostat_wohnzimmer_links        | heat       |
| media    | media_player.wohnbereich                   | paused     |
| media    | media_player.fernseher_im_wohnzimmer       | on         |
| media    | media_player.apple_tv_wohnzimmer           | off        |
| media    | media_player.xbox_series_s                 | off        |
| cover    | cover.rollo_terrassentur                   | open       |

### 3.2 zone:schlafbereich

**Context-Entities**

| Rolle        | Entity ID                                          | Aktuell    |
|--------------|----------------------------------------------------|------------|
| temperature  | sensor.sensor_schlafzimmer_air_temperature         | 20.0°C     |
| humidity     | sensor.sensor_schlafzimmer_humidity                | 46%        |
| brightness   | sensor.sensor_schlafzimmer_illuminance             | 0 lux      |
| motion       | binary_sensor.sensor_schlafzimmer_motion_detection | off        |
| window       | binary_sensor.sensor_fenster_schlafzimmer_window_door_is_open | off |
| presence     | binary_sensor.schlafzimmer_anwesenheit             | off        |
| humidity_dev | sensor.luftfeuchtigkeit_vocolino                   | 35%        |

**State-Entities**

| Rolle    | Entity ID                                  | Aktuell    |
|----------|--------------------------------------------|------------|
| lights   | light.beleuchtung_schlafzimmer             | on         |
| lights   | light.nachttischlampe                      | on         |
| media    | media_player.schlafbereich                 | idle       |

### 3.3 zone:kochbereich

**Context-Entities**

| Rolle        | Entity ID                                          | Aktuell    |
|--------------|----------------------------------------------------|------------|
| temperature  | sensor.thermostat_kochbereich_temperatur           | 21.48°C    |
| humidity     | sensor.thermostat_kochbereich_luftfeuchtigkeit     | 45.77%     |
| brightness   | sensor.sensor_presence_kuche_helligkeit             | 18 lux     |
| motion       | binary_sensor.sensor_presence_kuche_bewegung        | off        |
| presence     | binary_sensor.kuche_anwesenheit                     | off        |
| energy       | sensor.licht_kuche_power                            | 20.9W      |
| energy       | sensor.spulmaschine_electric_consumption_w          | 0.0W       |
| energy       | sensor.coca_cola_kuhlschrank_electric_consumption_w | 33.8W      |

**State-Entities**

| Rolle    | Entity ID                                  | Aktuell    |
|----------|--------------------------------------------|------------|
| lights   | light.beleuchtung_kuche                    | on         |
| lights   | light.licht_kuche                          | on         |
| lights   | light.licht_kuchenzeile                    | off        |
| heating  | climate.thermostat_kochbereich             | heat       |
| media    | media_player.kochbereich                   | idle       |

### 3.4 zone:badbereich

**Context-Entities**

| Rolle        | Entity ID                                          | Aktuell    |
|--------------|----------------------------------------------------|------------|
| temperature  | sensor.sensor_bad_temperatur                       | 21.6°C     |
| temperature  | sensor.sensor_toilette_temperatur                  | 23.0°C     |
| brightness   | sensor.sensor_bad_helligkeit                       | 0 lux      |
| brightness   | sensor.sensor_toilette_helligkeit                  | 34 lux     |
| motion       | binary_sensor.sensor_bad_bewegung                  | off        |
| motion       | binary_sensor.sensor_toilette_bewegung             | on         |
| presence     | binary_sensor.bad_anwesenheit                      | off        |
| presence     | binary_sensor.toilette_anwesenheit                 | on         |
| energy       | sensor.waschmaschine_electric_consumption_w        | 1.2W       |

**State-Entities**

| Rolle    | Entity ID                                  | Aktuell    |
|----------|--------------------------------------------|------------|
| lights   | light.beleuchtung_bad                      | off        |
| lights   | light.hue_badspiegel                       | on         |
| lights   | light.hue_toilette                         | on         |
| media    | media_player.badbereich                    | playing    |

### 3.5 zone:buero

**Context-Entities**

| Rolle        | Entity ID                                          | Aktuell    |
|--------------|----------------------------------------------------|------------|
| brightness   | sensor.sensor_arbeitszimmer_helligkeit             | 5 lux      |
| motion       | binary_sensor.sensor_arbeitszimmer_presence        | off        |
| presence     | binary_sensor.arbeitszimmer_anwesenheit            | off        |
| energy       | sensor.retroventilator_electric_consumption_w      | 0.0W       |

**State-Entities**

| Rolle    | Entity ID                                  | Aktuell    |
|----------|--------------------------------------------|------------|
| lights   | light.arbeitszimmer_beleuchtung            | on         |
| lights   | light.retrolampe                           | on         |
| lights   | light.shapes                               | off        |
| media    | media_player.buerobereich                  | playing    |
| media    | media_player.xbox_series_x                 | off        |

### 3.6 zone:gangbereich

**Context-Entities**

| Rolle        | Entity ID                                          | Aktuell    |
|--------------|----------------------------------------------------|------------|
| temperature  | sensor.thermostat_gangbereich_temperatur           | 18.5°C     |
| humidity     | sensor.thermostat_gangbereich_luftfeuchtigkeit     | 47.51%     |
| motion       | binary_sensor.sammelsensor_bewegung_gang           | off        |
| presence     | binary_sensor.gang_anwesenheit                     | on         |
| energy       | sensor.kaffeemaschine_electric_consumption_w       | 0.0W       |

**State-Entities**

| Rolle    | Entity ID                                  | Aktuell    |
|----------|--------------------------------------------|------------|
| lights   | light.beleuchtung_gang                     | off        |
| lights   | light.edisonlampe                          | off        |
| heating  | climate.thermostat_gangbereich             | heat       |
| media    | media_player.gangbereich                   | paused     |

### 3.7 zone:kinder

**Context-Entities**

| Rolle        | Entity ID                                          | Aktuell    |
|--------------|----------------------------------------------------|------------|
| temperature  | sensor.thermostat_zimmer_mira_temperatur           | 22.34°C    |
| temperature  | sensor.feuermelder_zimmer_paul_air_temperature     | 27.3°C     |
| humidity     | sensor.thermostat_zimmer_mira_luftfeuchtigkeit     | 45.14%     |
| humidity_dev | sensor.luftfeuchtigkeit_vocolina                   | 30%        |
| brightness   | sensor.sensor_zimmer_mira_illuminance              | 4.0 lux    |
| window       | binary_sensor.sensor_fenster_rechts_window_door_is_open | off   |
| window       | binary_sensor.sensor_fenster_links_window_door_is_open  | off   |
| window       | binary_sensor.sensor_dachfenster_window_door_is_open    | on    |
| smoke        | binary_sensor.feuermelder_zimmer_mira_smoke_detected    | off   |
| smoke        | binary_sensor.feuermelder_zimmer_paul_smoke_detected    | off   |
| presence     | binary_sensor.zimmer_mira_anwesenheit              | off        |

**State-Entities**

| Rolle    | Entity ID                                  | Aktuell    |
|----------|--------------------------------------------|------------|
| lights   | light.hue_zimmer_mira                      | on         |
| lights   | light.bettbeleuchtung_mira                 | on         |
| heating  | climate.thermostat_zimmer_mira             | heat       |

### 3.8 zone:aussen

**Context-Entities**

| Rolle        | Entity ID                                          | Aktuell    |
|--------------|----------------------------------------------------|------------|
| temperature  | sensor.terrasse_temperatur                         | 9.1°C      |
| humidity     | sensor.terrasse_luftfeuchtigkeit                   | 86%        |
| wind_speed   | sensor.windmesser_terrasse_windgeschwindigkeit     | 1 km/h     |
| wind_gust    | sensor.windmesser_terrasse_boenstarke              | 2 km/h     |
| rain         | sensor.regen_niederschlagsmenge_heute              | 0 mm       |
| motion       | binary_sensor.doorbell_repeater_5851_motion_sensor | off        |
| presence     | binary_sensor.terrasse_anwesenheit                 | off        |

**State-Entities**

| Rolle    | Entity ID                                  | Aktuell    |
|----------|--------------------------------------------|------------|
| lights   | light.beleuchtung_aussenbereich            | on         |
| lights   | light.gartenspots                          | off        |
| lights   | light.gartenscheinwerfer                   | off        |

---

## 4. Neuron-Mapping

Die 14 PilotSuite-Neuronen mappen auf echte Entities:

```
┌────────────────────┬───────────────────────────────────────────────┐
│ Neuron             │ Primaere Entity-Quellen                      │
├────────────────────┼───────────────────────────────────────────────┤
│ PresenceNeuron     │ binary_sensor.*_anwesenheit (pro Zone)       │
│                    │ binary_sensor.bewegung_* (FP2 Sub-Zonen)     │
│                    │ person.andreas, person.efka (Home/Away)       │
├────────────────────┼───────────────────────────────────────────────┤
│ TemperatureNeuron  │ sensor.thermostat_*_temperatur (pro Zone)    │
│                    │ sensor.sensor_*_air_temperature               │
│                    │ sensor.temperatur_wohnbereich_messstation     │
├────────────────────┼───────────────────────────────────────────────┤
│ HumidityNeuron     │ sensor.thermostat_*_luftfeuchtigkeit         │
│                    │ sensor.luftfeuchtigkeit_*_messstation         │
│                    │ sensor.sensor_*_humidity                      │
├────────────────────┼───────────────────────────────────────────────┤
│ LightNeuron        │ sensor.*_helligkeit (Hue Sensoren)           │
│                    │ sensor.sensor_*_illuminance (Aqara FP)       │
│                    │ light.beleuchtung_* (Gruppenlichter)         │
│                    │ binary_sensor.tageszeit_* (Morgen/Tag/Abend) │
├────────────────────┼───────────────────────────────────────────────┤
│ MediaNeuron        │ media_player.*bereich (Sonos Zonen)          │
│                    │ media_player.fernseher_im_wohnzimmer         │
│                    │ media_player.xbox_series_* (Gaming)          │
│                    │ media_player.apple_tv_wohnzimmer             │
├────────────────────┼───────────────────────────────────────────────┤
│ EnergyNeuron       │ sensor.stromverbrauch_paradiesgarten_21_*    │
│                    │ sensor.*_electric_consumption_w (pro Geraet) │
│                    │ sensor.ostausrichtung_estimated_*            │
│                    │ sensor.westausrichtung_geschatzte_*          │
│                    │ counter.gaszahler                            │
├────────────────────┼───────────────────────────────────────────────┤
│ WeatherNeuron      │ sensor.terrasse_temperatur (Aussen)          │
│                    │ sensor.terrasse_luftfeuchtigkeit             │
│                    │ sensor.windmesser_terrasse_*                 │
│                    │ sensor.regen_niederschlagsmenge_*            │
│                    │ binary_sensor.sturmwarnung                   │
│                    │ binary_sensor.sensor_hitzealarm              │
├────────────────────┼───────────────────────────────────────────────┤
│ AirQualityNeuron   │ sensor.co2_wohnbereich_messstation           │
│                    │ sensor.larm_wohnbereich_messstation (Noise)  │
│                    │ sensor.luftdruck_wohnbereich_messstation     │
│                    │ binary_sensor.sensor_luftqualitat_wohnzimmer │
├────────────────────┼───────────────────────────────────────────────┤
│ SecurityNeuron     │ binary_sensor.sensor_fenster_*_window_door_* │
│                    │ binary_sensor.feuermelder_*_smoke_detected   │
│                    │ camera.* (5 Kameras)                         │
│                    │ alarm_control_panel.* (3 Panels)             │
│                    │ binary_sensor.ai_360_person_erkannt          │
├────────────────────┼───────────────────────────────────────────────┤
│ ClimateNeuron      │ climate.thermostat_* (alle 6 Zonen)          │
│                    │ sensor.heat_generator_1_* (Wolf Heizung)     │
│                    │ sensor.direct_heating_circuit_*              │
├────────────────────┼───────────────────────────────────────────────┤
│ NetworkNeuron      │ sensor.ds1515_* (Synology NAS)               │
│                    │ sensor.dream_machine_special_edition_*       │
│                    │ switch.adguard_home_*                        │
├────────────────────┼───────────────────────────────────────────────┤
│ ApplianceNeuron    │ switch.kaffeemaschine / counter.kaffeemaschine│
│                    │ switch.spulmaschine                          │
│                    │ sensor.waschmaschine* (LG ThinQ)            │
│                    │ vacuum.saugi, vacuum.wischi                  │
├────────────────────┼───────────────────────────────────────────────┤
│ HealthNeuron       │ sensor.withings_gewicht                     │
│                    │ counter.toilette_whizzcount/shizzcount       │
│                    │ humidifier.vocolino, humidifier.vocolina     │
│                    │ sensor.luftfeuchtigkeit_vocolino/vocolina    │
├────────────────────┼───────────────────────────────────────────────┤
│ ContextNeuron      │ binary_sensor.tageszeit_* (4 Phasen)        │
│                    │ input_boolean.schlafmodus_smarthome          │
│                    │ input_select.heizmodus (Eco/Comfort)         │
│                    │ sensor.sun_nachste_morgendammerung           │
└────────────────────┴───────────────────────────────────────────────┘
```

---

## 5. Mood-Engine-Mapping

### 5.1 Comfort-Dimension (0.0 - 1.0)

```python
COMFORT_RULES = {
    # Positive Faktoren
    "temp_optimal":     "22 <= avg(sensor.thermostat_*_temperatur) <= 24 → +0.3",
    "humidity_optimal":  "40 <= avg(sensor.*_luftfeuchtigkeit) <= 60 → +0.2",
    "co2_low":          "sensor.co2_wohnbereich_messstation < 800 → +0.15",
    "noise_low":        "sensor.larm_wohnbereich_messstation < 50 → +0.15",
    "light_appropriate": "Tageszeit-abhaengige Beleuchtung → +0.2",

    # Negative Faktoren
    "temp_cold":        "avg(temp) < 18 → -0.3",
    "co2_high":         "co2 > 1200 → -0.3",
    "noise_high":       "noise > 70 → -0.2",
    "window_open_cold": "Fenster offen + Aussen < 10°C → -0.2",
}
```

### 5.2 Joy-Dimension (0.0 - 1.0)

```python
JOY_RULES = {
    "music_playing":    "media_player.*bereich == playing → +0.25",
    "tv_on":           "media_player.fernseher* == on → +0.15",
    "gaming":          "media_player.xbox_series_* == on → +0.2",
    "social_presence":  "count(person.* == home) >= 2 → +0.15",
    "outdoor_nice":    "Terrasse temp > 15°C + kein Regen → +0.1",
    "coffee_recent":   "Kaffeemaschine kuerzlich aktiv → +0.1",
    "night_alone":     "Nacht + nur 1 Person home → -0.1",
}
```

### 5.3 Frugality-Dimension (0.0 - 1.0)

```python
FRUGALITY_RULES = {
    "solar_producing":  "PV Produktion > 500W → +0.3",
    "solar_covers":    "Produktion > Verbrauch → +0.2",
    "low_energy":      "Gesamtverbrauch < 500W → +0.2",
    "eco_heating":     "input_select.heizmodus == Eco → +0.15",
    "high_energy":     "Gesamtverbrauch > 2000W → -0.2",
    "standby_waste":   "Viele Geraete on bei niemand zuhause → -0.3",
}
```

---

## 6. Beispielkonfiguration (YAML)

### 6.1 Zonen-Konfiguration

```yaml
# habitus_zones.yaml — PilotSuite v10.5
zones:
  - zone_id: "zone:wohnbereich"
    name: "Wohnbereich"
    zone_type: "area"
    floor: "EG"
    priority: 9
    tags:
      - "aicp.place.wohnzimmer"
      - "aicp.place.wohnbereich"
    entities:
      motion:
        - binary_sensor.bewegung_wohnzimmer
        - binary_sensor.bewegung_grosse_couch
        - binary_sensor.bewegung_kleine_couch
        - binary_sensor.bewegung_spielwiese
        - binary_sensor.bewegung_schnapsschrank
        - binary_sensor.bewegung_durchgangsbereich_wohnbereich
      lights:
        - light.beleuchtung_wohnzimmer
        - light.deckenlicht
        - light.beleuchtung_durchgangsbereich
        - light.beleuchtung_terrassentur
      temperature:
        - sensor.thermostat_wohnzimmer_rechts_temperatur
        - sensor.thermostat_wohnzimmer_links_temperatur
        - sensor.temperatur_wohnbereich_messstation
      humidity:
        - sensor.thermostat_wohnzimmer_rechts_luftfeuchtigkeit
        - sensor.thermostat_wohnzimmer_links_luftfeuchtigkeit
        - sensor.luftfeuchtigkeit_wohnbereich_messstation
      co2:
        - sensor.co2_wohnbereich_messstation
      noise:
        - sensor.larm_wohnbereich_messstation
      brightness:
        - sensor.helligkeit_wohnzimmer
      heating:
        - climate.thermostat_wohnzimmer_rechts
        - climate.thermostat_wohnzimmer_links
      media:
        - media_player.wohnbereich
        - media_player.fernseher_im_wohnzimmer
        - media_player.apple_tv_wohnzimmer
        - media_player.xbox_series_s
      cover:
        - cover.rollo_terrassentur
      power:
        - sensor.steckerleiste_wohnzimmer_electric_consumption_w
        - sensor.steckerleiste_wohnzimmer_electric_consumption_w_2
        - sensor.deckenlicht_links_electric_consumption_w
        - sensor.deckenlicht_rechts_electric_consumption_w

  - zone_id: "zone:schlafbereich"
    name: "Schlafbereich"
    zone_type: "room"
    floor: "EG"
    priority: 8
    tags:
      - "aicp.place.schlafzimmer"
    entities:
      motion:
        - binary_sensor.sensor_schlafzimmer_motion_detection
      lights:
        - light.beleuchtung_schlafzimmer
        - light.nachttischlampe
      temperature:
        - sensor.sensor_schlafzimmer_air_temperature
      humidity:
        - sensor.sensor_schlafzimmer_humidity
        - sensor.luftfeuchtigkeit_vocolino
      brightness:
        - sensor.sensor_schlafzimmer_illuminance
      window:
        - binary_sensor.sensor_fenster_schlafzimmer_window_door_is_open
      media:
        - media_player.schlafbereich

  - zone_id: "zone:kochbereich"
    name: "Kochbereich"
    zone_type: "area"
    floor: "EG"
    priority: 7
    child_zone_ids:
      - "zone:speisekammer"
    tags:
      - "aicp.place.kueche"
    entities:
      motion:
        - binary_sensor.sensor_presence_kuche_bewegung
      lights:
        - light.beleuchtung_kuche
        - light.licht_kuche
        - light.licht_kuchenzeile
        - light.licht_spule
      temperature:
        - sensor.thermostat_kochbereich_temperatur
      humidity:
        - sensor.thermostat_kochbereich_luftfeuchtigkeit
      brightness:
        - sensor.sensor_presence_kuche_helligkeit
      heating:
        - climate.thermostat_kochbereich
      media:
        - media_player.kochbereich
      power:
        - sensor.licht_kuche_power
        - sensor.spulmaschine_electric_consumption_w
        - sensor.coca_cola_kuhlschrank_electric_consumption_w

  - zone_id: "zone:badbereich"
    name: "Badbereich"
    zone_type: "area"
    floor: "EG"
    priority: 6
    tags:
      - "aicp.place.bad"
      - "aicp.place.toilette"
    entities:
      motion:
        - binary_sensor.sensor_bad_bewegung
        - binary_sensor.sensor_toilette_bewegung
      lights:
        - light.beleuchtung_bad
        - light.hue_badspiegel
        - light.hue_toilette
      temperature:
        - sensor.sensor_bad_temperatur
        - sensor.sensor_toilette_temperatur
      brightness:
        - sensor.sensor_bad_helligkeit
        - sensor.sensor_toilette_helligkeit
      media:
        - media_player.badbereich
      power:
        - sensor.waschmaschine_electric_consumption_w
        - sensor.licht_badspiegel_electric_consumption_w
        - sensor.licht_toilette_electric_consumption_w

  - zone_id: "zone:buero"
    name: "Buerobereich"
    zone_type: "room"
    floor: "EG"
    priority: 8
    tags:
      - "aicp.place.arbeitszimmer"
      - "aicp.place.buero"
    entities:
      motion:
        - binary_sensor.sensor_arbeitszimmer_presence
      lights:
        - light.arbeitszimmer_beleuchtung
        - light.retrolampe
        - light.shapes
        - light.hue_lightguide
      brightness:
        - sensor.sensor_arbeitszimmer_helligkeit
      media:
        - media_player.buerobereich
        - media_player.xbox_series_x
        - media_player.fire_tv_2
      power:
        - sensor.retroventilator_electric_consumption_w

  - zone_id: "zone:gangbereich"
    name: "Gangbereich"
    zone_type: "area"
    floor: "EG"
    priority: 4
    tags:
      - "aicp.place.gang"
      - "aicp.place.flur"
      - "aicp.place.vorraum"
    entities:
      motion:
        - binary_sensor.sammelsensor_bewegung_gang
        - binary_sensor.sensor_gang_motion_detection
      lights:
        - light.beleuchtung_gang
        - light.edisonlampe
        - light.treppenlicht
      temperature:
        - sensor.thermostat_gangbereich_temperatur
        - sensor.sensor_gang_air_temperature
      humidity:
        - sensor.thermostat_gangbereich_luftfeuchtigkeit
      heating:
        - climate.thermostat_gangbereich
      media:
        - media_player.gangbereich
      power:
        - sensor.kaffeemaschine_electric_consumption_w

  - zone_id: "zone:kinder"
    name: "Kinderbereich"
    zone_type: "area"
    floor: "EG"
    priority: 7
    tags:
      - "aicp.place.kinderzimmer"
      - "aicp.place.zimmer_mira"
      - "aicp.place.zimmer_paul"
    entities:
      motion:
        - binary_sensor.sensor_zimmer_mira_sensor_state_any
      lights:
        - light.hue_zimmer_mira
        - light.bettbeleuchtung_mira
      temperature:
        - sensor.thermostat_zimmer_mira_temperatur
        - sensor.feuermelder_zimmer_paul_air_temperature
      humidity:
        - sensor.thermostat_zimmer_mira_luftfeuchtigkeit
        - sensor.luftfeuchtigkeit_vocolina
      brightness:
        - sensor.sensor_zimmer_mira_illuminance
      window:
        - binary_sensor.sensor_fenster_rechts_window_door_is_open
        - binary_sensor.sensor_fenster_links_window_door_is_open
        - binary_sensor.sensor_dachfenster_window_door_is_open
      heating:
        - climate.thermostat_zimmer_mira

  - zone_id: "zone:loft"
    name: "Loft"
    zone_type: "room"
    floor: "OG"
    priority: 3
    tags:
      - "aicp.place.loft"
    entities:
      lights:
        - light.beleuchtung_loft
        - light.licht_spassecke
        - light.flutlicht_loft
      media:
        - media_player.sony_x77
      power:
        - sensor.flutlicht_loft_electric_consumption_w
        - sensor.smart_plug_netzwerkdienste_leistung

  - zone_id: "zone:aussen"
    name: "Aussenbereich"
    zone_type: "outdoor"
    floor: "EG"
    priority: 2
    tags:
      - "aicp.place.terrasse"
      - "aicp.place.garten"
    entities:
      motion:
        - binary_sensor.doorbell_repeater_5851_motion_sensor
      lights:
        - light.beleuchtung_aussenbereich
        - light.gartenspots
        - light.gartenscheinwerfer
      temperature:
        - sensor.terrasse_temperatur
      humidity:
        - sensor.terrasse_luftfeuchtigkeit
```

### 6.2 Options-Flow Konfiguration

```yaml
# Integration Config Entry Optionen
ai_home_copilot:
  core_url: "http://localhost:8909"
  scan_interval: 120
  event_batch_size: 20
  event_batch_interval: 10

  # Household
  household_name: "SmartHome Paradiesgarten"
  household_members:
    - name: "Andreas"
      person_entity: "person.andreas"
      role: "admin"
      age_group: "adult"
    - name: "Efka"
      person_entity: "person.efka"
      role: "member"
      age_group: "adult"
    - name: "Mira"
      person_entity: "person.mira"
      role: "child"
      age_group: "child"
    - name: "Pauli"
      person_entity: "person.pauli"
      role: "child"
      age_group: "child"

  # Character
  character_preset: "copilot"
  character_language: "de"

  # LLM
  llm_provider: "ollama"
  llm_model: "qwen3:0.6b"

  # Features
  brain_graph_enabled: true
  habitus_mining_enabled: true
  proactive_suggestions_enabled: true
  conversation_memory_enabled: true
  energy_monitoring_enabled: true
  media_context_enabled: true
  weather_context_enabled: true
  network_monitoring_enabled: true
  security_monitoring_enabled: true

  # Zone Automation
  zone_automation_enabled: true
  zone_automation_light_mode: "auto"
  zone_automation_target_lux: 300
  zone_automation_circadian_enabled: true
  zone_automation_media_follow: true
```

---

## 7. Dashboard-Konzept

### 7.1 Drei-Saeulen-Architektur

```
┌─────────────────────────────────────────────────────────┐
│                  PILOTSUITE DASHBOARD                    │
├──────────────┬──────────────────┬────────────────────────┤
│  HABITUS     │  HAUSVERWALTUNG  │        STYX            │
│  (Mood/Zone) │  (Management)    │  (Neural Intelligence) │
├──────────────┼──────────────────┼────────────────────────┤
│              │                  │                        │
│ Zone-Status  │ Energie-Monitor  │ Brain Graph            │
│ Mood-Gauges  │ Sicherheit       │ Neuron-Layers          │
│ Comfort-Map  │ Geraete-Status   │ Suggestions            │
│ Presence-Map │ Wartung          │ Habitus-Patterns       │
│ Zone-History │ Haushalt         │ Chat-Interface         │
│              │                  │                        │
└──────────────┴──────────────────┴────────────────────────┘
```

### 7.2 Tab 1: Habitus-Zonen (Primaer-Ansicht)

```
┌─────────────────────────────────────────────────────────┐
│ [Stimmungslage: Entspannt]  Wohnbereich aktiv  19:15    │
├─────────────┬───────────────────────────────────────────┤
│ ZONE-GRID   │           AKTIVE ZONE DETAIL              │
│             │                                           │
│ [WZ] ●      │  Wohnbereich                    Prio: 9  │
│ [SZ] ○      │  ┌─────────┬─────────┬─────────┐         │
│ [KU] ○      │  │Comfort  │  Joy    │Frugality│         │
│ [BA] ◑      │  │  0.78   │  0.62   │  0.45   │         │
│ [BU] ◑      │  │  ████▓  │  ████░  │  ███░░  │         │
│ [GA] ○      │  └─────────┴─────────┴─────────┘         │
│ [KI] ○      │                                           │
│ [LO] ○      │  22.4°C  42%  721ppm  62dB  13lux        │
│ [AU] ○      │  ┌────┐ ┌────┐ ┌────┐ ┌────┐             │
│             │  │ TV │ │Sono│ │Licht││Roll│             │
│ ● aktiv     │  │ on │ │paus│ │ on ││open│             │
│ ◑ teilaktiv │  └────┘ └────┘ └────┘ └────┘             │
│ ○ inaktiv   │                                           │
│             │  Letzte Bewegung: Durchgang (vor 2m)      │
│             │  Personen: Andreas, Efka (home)           │
└─────────────┴───────────────────────────────────────────┘
```

### 7.3 Tab 2: Hausverwaltung

```
┌─────────────────────────────────────────────────────────┐
│ HAUSVERWALTUNG                            Paradiesgarten│
├──────────────────┬──────────────────────────────────────┤
│ ENERGIE          │  SICHERHEIT                          │
│                  │                                      │
│ PV Heute: 37.8kWh│  Tueren/Fenster:                    │
│ Verbrauch: 891W  │    Schlafzimmer: ✓ geschlossen      │
│ Produktion: 803W │    Kinderzimmer R: ✓ geschlossen    │
│ Bilanz: -88W     │    Kinderzimmer L: ✓ geschlossen    │
│                  │    Dachfenster: ⚠ OFFEN              │
│ Gas: 67010 m³    │                                      │
│ Heizung: Eco     │  Rauchmelder: ✓ alle OK             │
│ Brenner: aus     │  Kameras: 5 aktiv                    │
│ Vorlauf: 44.2°C  │  Alarme: alle disarmed              │
│                  │                                      │
├──────────────────┼──────────────────────────────────────┤
│ GERAETE          │  NETZWERK                            │
│                  │                                      │
│ Waschmaschine:off│  UniFi: 2 Clients, 36.9% CPU       │
│ Spuelmaschine:on │  NAS: Vol4 ⚠ 90.4% (danger)        │
│ Kaffeemaschine:  │       Disk3 ⚠ CRASHED               │
│   15297 Bezuege  │  AdGuard: Schutz aktiv              │
│   856 Reinigungen│  System: 38.1% RAM, 5% CPU          │
│ Saugi: docked    │  Speicher: 89.5% belegt ⚠           │
│ Wischi: docked   │  Uptime: 3d 9h                      │
│                  │                                      │
├──────────────────┼──────────────────────────────────────┤
│ HAUSHALT         │  WETTER                              │
│                  │                                      │
│ Andreas: zuhause │  9.1°C, 86% Luftf.                  │
│ Efka: zuhause    │  Wind: 1 km/h O                     │
│ Mira: unbekannt  │  Regen: 0mm heute                   │
│ Pauli: unbekannt │  PV morgen: ~34 kWh                 │
│                  │  Heizmodus: Eco                      │
│ Tageszeit: Abend │  Brenner: Taktsperre                │
└──────────────────┴──────────────────────────────────────┘
```

### 7.4 Tab 3: Styx (Neural Intelligence)

```
┌─────────────────────────────────────────────────────────┐
│ STYX NEURAL DASHBOARD                    Pipeline: OK   │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              BRAIN GRAPH (vis.js)                 │   │
│  │                                                    │   │
│  │     [Wohnzimmer]──[TV]──[Sonos]                   │   │
│  │          │    \                                     │   │
│  │     [Presence]  [Thermostat]──[Heizung]           │   │
│  │          │                                         │   │
│  │     [Andreas]──[Home]                             │   │
│  │                                                    │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  NEURON LAYERS                                           │
│  ┌────────┬────────┬────────┬────────┬────────┐         │
│  │Context │ State  │ Mood   │Pattern │Suggest.│         │
│  │ ✓ 14   │ ✓ 9   │ ✓ 3   │ ● 12  │ ○ 0   │         │
│  └────────┴────────┴────────┴────────┴────────┘         │
│                                                          │
│  AKTUELLE VORSCHLAEGE                                    │
│  ┌──────────────────────────────────────────────┐       │
│  │ 💡 CO2 im Wohnbereich steigt (721 ppm)       │       │
│  │    → Fenster oeffnen fuer bessere Luft       │       │
│  │    [Akzeptieren] [Spaeter] [Ablehnen]        │       │
│  ├──────────────────────────────────────────────┤       │
│  │ 🌡 Dachfenster Zimmer Paul ist offen          │       │
│  │    → Bei 9.1°C Aussentemp. schliessen?       │       │
│  │    [Akzeptieren] [Spaeter] [Ablehnen]        │       │
│  └──────────────────────────────────────────────┘       │
│                                                          │
│  CHAT MIT PILOTSUITE                                     │
│  ┌──────────────────────────────────────────────┐       │
│  │ > Wie ist die aktuelle Stimmung im Haus?     │       │
│  │                                               │       │
│  │ Das Haus ist in einer entspannten Abend-     │       │
│  │ stimmung. Im Wohnbereich laeuft Musik        │       │
│  │ (pausiert), der TV ist an. Die Temperatur    │       │
│  │ ist mit 22-24°C angenehm. Der CO2-Wert      │       │
│  │ von 721 ppm ist noch akzeptabel aber steigt. │       │
│  │ [____________________________________] [↵]   │       │
│  └──────────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────────┘
```

---

## 8. Implementierungskonzept

### 8.1 Phasen-Plan

```
Phase 1: Zone-Konfiguration (v10.5.1)
├── Auto-Discovery: HA Areas → Habitus Zones (auto_setup.py)
├── Entity-Classifier: Role-Mapping per Entity (entity_classifier.py)
├── Zone-Store: Persistenz der Zuordnung (habitus_zones_store_v2.py)
└── Validierung: Testen mit echten Entities

Phase 2: Neuron-Integration (v10.5.2)
├── Entity-Watcher pro Zone: State-Changes tracken
├── Neuron-Inputs verdrahten: Echte Entity-States → Neuron-Pipeline
├── Mood-Engine: Comfort/Joy/Frugality aus echten Werten
└── Proaktive Suggestions: Mood-Triggers aktivieren

Phase 3: Dashboard-Cards (v10.5.3)
├── Zone-Status-Card: Mood-Gauges + Sensor-Werte
├── Hausverwaltung-Card: Energie + Sicherheit + Geraete
├── Styx-Card: Brain Graph + Neurons + Chat
└── Responsive Layout: 3-Tab Navigation

Phase 4: Chat & Conversation (v10.5.4)
├── WebSocket Chat (bereits implementiert in v10.5.0)
├── Conversation Memory mit echtem Kontext
├── Character-Preset "Andreas" (Deutsch, Smart-Home Experte)
└── Proaktive Suggestions via Chat
```

### 8.2 Kritische Dateien

| Phase | Datei (styx-ha)                        | Aenderung                        |
|-------|----------------------------------------|----------------------------------|
| 1     | `core/modules/auto_setup.py`           | HA Area → Zone Mapping           |
| 1     | `ml/entity_classifier.py`              | Role-Detection fuer Zone-Entities|
| 1     | `habitus_zones_store_v2.py`            | Persistenz + Conflict Resolution |
| 2     | `events_forwarder.py`                  | Zone-gefiltertes Event Forwarding|
| 2     | `mood_context_module.py`               | Echte Entity-States → Mood       |
| 2     | `sensors/mood_sensors.py`              | Live Comfort/Joy/Frugality       |
| 3     | `dashboard_cards/habitus_dashboard.py` | Zone-Status Card Generator       |
| 3     | `dashboard_cards/hausverwaltung.py`    | Management Overview Card         |
| 3     | `dashboard_cards/styx_dashboard.py`    | Neural Intelligence Card         |
| 4     | `suggestion_panel.py`                  | Chat WebSocket (bereits fertig)  |

| Phase | Datei (styx-core)                      | Aenderung                        |
|-------|----------------------------------------|----------------------------------|
| 2     | `neurons/manager.py`                   | Zone-spezifische Pipeline        |
| 2     | `mood/mood_engine.py`                  | Comfort/Joy/Frugality Scoring    |
| 2     | `proactive_engine.py`                  | Mood-Trigger → Suggestions       |
| 4     | `api/v1/conversation.py`               | Multi-Turn mit Memory (fertig)   |
| 4     | `conversation_memory.py`               | Lifelong Learning (fertig)       |

### 8.3 Daten-Fluss (End-to-End)

```
HA Entity State Change
  │
  ▼
EventsForwarder (batched, PII-redacted, zone-tagged)
  │
  ▼
Core: Event Ingest → Brain Graph (node + edge updates)
  │
  ▼
Core: NeuronManager.run_pipeline()
  ├── Context Layer (14 Neurons: Presence, Temp, Humidity, ...)
  ├── State Layer (aggregiert Context → Zone-States)
  ├── Mood Layer (Comfort, Joy, Frugality per Zone)
  └── Proactive Layer (Mood Triggers → Suggestions)
  │
  ▼
Core: Candidates Store (pending → offered)
  │
  ▼
HA: CandidatePoller → Repairs UI / Dashboard
  │
  ▼
User: Accept / Dismiss / Chat
  │
  ▼
HA: WebSocket → Core: Conversation API
  ├── Conversation Memory (Lifelong Learning)
  ├── Preference Extraction
  └── Brain Graph Enrichment
```

### 8.4 Sofort-Warnungen (aus Live-Daten)

| Prioritaet | Problem                                            | Aktion              |
|------------|----------------------------------------------------|--------------------|
| HOCH       | NAS Disk 3: **crashed**                            | SecurityNeuron Alert|
| HOCH       | NAS Vol 4: **90.4%** (danger)                      | Vorschlag: Aufraeum.|
| MITTEL     | HA Speicher: **89.5%** belegt                      | System Health Alert |
| MITTEL     | Dachfenster Paul: **offen** bei 9.1°C Aussen       | Comfort Suggestion  |
| NIEDRIG    | CO2 Wohnbereich: **721 ppm** (steigend)            | Lueften-Vorschlag   |
| NIEDRIG    | OpenAI Provider: **error** (404)                   | Network Neuron Log  |
| INFO       | 436 fehlende Entities (Watchman)                   | Hygiene-Vorschlag   |

---

## 9. Zusammenfassung

### Was bereits implementiert ist (v10.5.0):

- ✅ Multi-Turn Conversation Memory (Core)
- ✅ WebSocket Chat Command (HA)
- ✅ Proaktive Mood Suggestions (Core + HA Webhook)
- ✅ Zone Store v2 mit Conflict Resolution
- ✅ Entity Classifier ML Pipeline
- ✅ 14 Neuron Types
- ✅ Brain Graph mit Persistenz
- ✅ Habitus Mining Engine
- ✅ 800+ Tests (691 HA + 109 Core)

### Was als Naechstes kommt (v10.5.1-10.5.4):

- 🔲 Auto-Discovery: HA Areas → Habitus Zones mit echten Entities
- 🔲 Neuron-Verdrahtung: Echte Entity-States in die Pipeline
- 🔲 3-Tab Dashboard: Habitus + Hausverwaltung + Styx
- 🔲 Proaktive Suggestions: Live aus dem echten SmartHome
- 🔲 Chat mit Kontext: "Wie warm ist es?" → echte Temperatur-Daten

### Metriken:

| Metrik                  | Wert         |
|-------------------------|-------------|
| Physische Raeume        | 15           |
| Habitus-Zonen           | 9 + 4 Infra  |
| Gemappte Entities       | ~250 (Kern)  |
| Total HA Entities       | 4520         |
| Neuron-Types            | 14           |
| Mood-Dimensionen        | 3 (C/J/F)    |
| Sonos-Zonen             | 6            |
| Kameras                 | 5            |
| Thermostats             | 6            |
| Bewohner                | 7            |
