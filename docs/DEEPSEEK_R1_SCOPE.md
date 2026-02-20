# AI Home CoPilot — DeepSeek-R1 Ollama Scope & Anweisungen

> Dieses Dokument definiert den Scope und die Anweisungen für das lokale
> DeepSeek-R1 Modell (Ollama), das als offline LLM-Backend für den
> AI Home CoPilot dient.

---

## 1) Projektkontext

Das AI Home CoPilot Projekt besteht aus **zwei Repositories**:

| Repo | Zweck | Version |
|------|-------|---------|
| `ai-home-copilot-ha` | Home Assistant Custom Integration (Frontend/Adapter) | 0.3.2 |
| `Home-Assistant-Copilot` | Copilot-Core Add-on (Backend/Intelligence) | 0.2.7 |

**Architektur-Überblick:**
```
Home Assistant
  └── ai_home_copilot Integration (Repo 1)
        ├── Webhook-Empfänger / Events Forwarder
        ├── Suggestions Pipeline + Repairs UI
        ├── Habitus Zones + Entity Plattformen
        └── Observability (DevLogs, Error Digest)
              │
              │ HTTP REST (:8909)
              ▼
  └── copilot_core Add-on (Repo 2)
        ├── Event Store (idempotent, Ring-Buffer)
        ├── Brain Graph (Decay, Pruning)
        ├── Candidate Generation
        ├── Mood Scoring (Heuristik)
        └── API v1 Endpoints
```

---

## 2) Rolle des DeepSeek-R1 Modells

Das DeepSeek-R1 Modell läuft **lokal via Ollama** und wird als
**offline-fähiges Reasoning-Backend** eingesetzt. Es ersetzt KEINE
bestehende Logik, sondern **ergänzt** die heuristische Pipeline.

### Einsatzbereiche (Scope)

| Bereich | Aufgabe | Priorität |
|---------|---------|-----------|
| **Kandidaten-Bewertung** | Bewerte generierte A→B Kandidaten auf Plausibilität und Nützlichkeit | HOCH |
| **Erklärungen generieren** | Erstelle menschenlesbare Begründungen für Suggestions (warum Automatisierung X sinnvoll ist) | HOCH |
| **Seed-Analyse** | Analysiere Seed-Sensor-Daten und extrahiere sinnvolle Automatisierungsvorschläge | MITTEL |
| **Log-Analyse** | Analysiere HA-Fehlerlogs und schlage Fixes vor | MITTEL |
| **Habitus-Insights** | Erkenne Muster in Zone-Aktivitäten und generiere Insights | NIEDRIG |
| **Mood-Verfeinerung** | Verfeinere das Mood-Scoring mit kontextuellem Reasoning | NIEDRIG |

### Explizit NICHT im Scope

- Direkte Steuerung von HA-Entities (Governance-first!)
- Zugriff auf persönliche Daten außerhalb des definierten Kontexts
- Eigenständige Automatisierungserstellung ohne User-Bestätigung
- Internet-Zugriff oder Cloud-Kommunikation
- Medizinische/Gesundheits-Bewertungen

---

## 3) Integration in die bestehende Architektur

### 3.1 Einbindungspunkt: Copilot-Core (Repo 2)

```
copilot_core/
  └── llm/                          # NEU: LLM-Abstraktionsschicht
      ├── __init__.py
      ├── provider.py               # OllamaProvider (HTTP → localhost:11434)
      ├── prompts.py                # Prompt-Templates pro Aufgabe
      └── schemas.py                # Structured Output Schemas
```

**API-Kommunikation:**
```
Copilot-Core  ──HTTP──▶  Ollama (localhost:11434)
                          └── deepseek-r1 Modell
```

### 3.2 Prompt-Design Regeln

1. **System-Prompt**: Immer mit Rolle + Kontext + Einschränkungen
2. **Sprache**: Deutsch als Primärsprache, Englisch für technische Begriffe
3. **Strukturierte Ausgabe**: JSON-Schema für maschinenlesbare Antworten
4. **Token-Limit**: Max 2048 Output-Tokens pro Request (Ressourcenschonung)
5. **Temperatur**: 0.3 für Bewertungen, 0.7 für Erklärungen

### 3.3 Beispiel: Kandidaten-Bewertung

**Input an DeepSeek-R1:**
```json
{
  "task": "evaluate_candidate",
  "candidate": {
    "trigger": "binary_sensor.motion_flur",
    "action": "light.flur_decke",
    "pattern": "A→B",
    "support": 42,
    "confidence": 0.85,
    "time_window": "18:00-23:00"
  },
  "context": {
    "zone": "Flur",
    "zone_entities": ["binary_sensor.motion_flur", "light.flur_decke", "light.flur_wand"]
  }
}
```

**Erwartete Ausgabe:**
```json
{
  "score": 0.82,
  "recommendation": "accept",
  "explanation": "Bewegungsmelder im Flur löst zuverlässig (85% Konfidenz) das Deckenlicht aus, besonders abends. Dies ist ein klassisches Automatisierungsmuster mit hohem Nutzwert.",
  "risks": ["Licht könnte bei Durchgangsbewegung unnötig angehen"],
  "suggestions": ["Timer für automatisches Ausschalten nach 5 Min ergänzen"]
}
```

---

## 4) Governance-Regeln für LLM-Integration

> Basierend auf ETHICS_GOVERNANCE.md — diese Regeln sind **nicht verhandelbar**.

### 4.1 Privacy-first
- DeepSeek-R1 läuft **ausschließlich lokal** (Ollama, kein Cloud-Fallback)
- **Keine** Entity-IDs, Namen, oder persönliche Daten in Logs schreiben
- Prompt-Inhalte werden **nicht** persistiert (nur strukturierte Ergebnisse)
- Token/Secrets werden **vor** LLM-Aufruf aus dem Kontext entfernt

### 4.2 Governance-first
- LLM-Ergebnisse sind **Vorschläge**, keine Aktionen
- Jeder LLM-Vorschlag durchläuft die bestehende Candidate-Pipeline
- User-Bestätigung via Repairs UI bleibt **immer** erforderlich
- LLM-Score fließt als **ein Faktor** in die Bewertung ein (nicht allein entscheidend)

### 4.3 Explainability
- Jede LLM-Bewertung muss eine `explanation` enthalten
- Erklärungen werden in der Repairs-UI dem User angezeigt
- Bei Unsicherheit: "Ich bin mir nicht sicher" > falsche Zuversicht

### 4.4 Safety
- Timeout: Max 30 Sekunden pro LLM-Request
- Fallback: Bei LLM-Fehler → heuristische Bewertung (bestehende Logik)
- Rate-Limit: Max 20 LLM-Calls pro Stunde
- Kein Retry-Storm: Max 1 Retry bei Timeout, dann Fallback

---

## 5) Technische Anforderungen

### 5.1 Ollama Setup
```yaml
# Erwartete Ollama-Konfiguration
host: localhost
port: 11434
model: deepseek-r1           # oder deepseek-r1:7b / :14b je nach Hardware
keep_alive: 5m                # Modell 5 Min im RAM halten
```

### 5.2 Hardware-Empfehlung
| Modell-Variante | RAM | GPU VRAM | Empfehlung |
|----------------|-----|----------|------------|
| deepseek-r1:1.5b | 4 GB | - | Raspberry Pi 5 (8GB) — nur Basis-Tasks |
| deepseek-r1:7b | 8 GB | 6 GB | Mini-PC / NUC — empfohlen für Heimserver |
| deepseek-r1:14b | 16 GB | 12 GB | Dedizierter Server — volle Qualität |
| deepseek-r1:32b | 32 GB | 24 GB | High-End — maximale Qualität |

### 5.3 API-Endpunkte (Copilot-Core Erweiterung)

```
POST /api/v1/llm/evaluate     # Kandidaten bewerten
POST /api/v1/llm/explain       # Erklärung generieren
POST /api/v1/llm/analyze-logs  # Log-Analyse
GET  /api/v1/llm/status        # LLM-Verfügbarkeit prüfen
```

### 5.4 Konfiguration (Add-on Options)
```json
{
  "llm_enabled": false,
  "llm_provider": "ollama",
  "llm_host": "localhost",
  "llm_port": 11434,
  "llm_model": "deepseek-r1",
  "llm_timeout_seconds": 30,
  "llm_max_calls_per_hour": 20,
  "llm_temperature_evaluation": 0.3,
  "llm_temperature_explanation": 0.7,
  "llm_max_output_tokens": 2048
}
```

---

## 6) Implementierungsreihenfolge

### Phase 1: Grundlagen (MVP)
1. Ollama-Provider in Copilot-Core implementieren
2. Health-Check Endpoint (`GET /api/v1/llm/status`)
3. Kandidaten-Bewertung mit strukturiertem Output
4. Fallback auf Heuristik bei LLM-Ausfall
5. HA-Integration: LLM-Status als Sensor

### Phase 2: Erklärungen
1. Explanation-Generator für Repairs-UI
2. Deutsche Prompt-Templates
3. Erklärungen in Candidate-Payload integrieren

### Phase 3: Erweiterte Analyse
1. Log-Analyse Endpoint
2. Seed-Sensor Analyse
3. Habitus-Insights aus Zone-Daten

### Phase 4: Verfeinerung
1. Prompt-Tuning basierend auf User-Feedback
2. Mood-Scoring Verfeinerung
3. Adaptive Temperatur basierend auf Task-Typ

---

## 7) Prompt-Templates (Entwürfe)

### System-Prompt (Basis)
```
Du bist der AI Home CoPilot — ein lokaler, privacy-first Assistent für
Home Assistant Automatisierung. Du analysierst Muster und bewertest
Automatisierungsvorschläge.

Regeln:
- Du SCHLÄGST VOR, du FÜHRST NICHT AUS.
- Du erklärst WARUM, nicht nur WAS.
- Bei Unsicherheit sage "Ich bin mir nicht sicher".
- Antworte auf Deutsch.
- Antworte im geforderten JSON-Format.
- Keine medizinischen oder gesundheitlichen Aussagen.
```

### Kandidaten-Bewertung
```
Bewerte diesen Automatisierungsvorschlag für ein Smart Home:

Trigger: {trigger_entity} (Typ: {trigger_domain})
Aktion: {action_entity} (Typ: {action_domain})
Muster: {pattern_type}
Häufigkeit: {support} mal beobachtet
Konfidenz: {confidence}%
Zeitfenster: {time_window}
Zone: {zone_name}

Antworte als JSON:
{
  "score": <0.0-1.0>,
  "recommendation": "<accept|review|reject>",
  "explanation": "<2-3 Sätze warum>",
  "risks": ["<mögliche Risiken>"],
  "suggestions": ["<Verbesserungsvorschläge>"]
}
```

### Log-Analyse
```
Analysiere diese Home Assistant Fehlermeldungen und schlage Lösungen vor:

{log_entries}

Antworte als JSON:
{
  "issues": [
    {
      "severity": "<critical|warning|info>",
      "component": "<betroffene Integration>",
      "summary": "<Kurzbeschreibung>",
      "fix_suggestion": "<Lösungsvorschlag>",
      "reversible": <true|false>
    }
  ]
}
```
