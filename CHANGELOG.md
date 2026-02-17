# Changelog - PilotSuite Core Add-on

## [0.9.1-alpha.8] - 2026-02-17

### Added
- **OpenAI Chat Completions API:** OpenClaw Assistant als OpenAI-kompatibler Chat Endpoint
  - `/api/v1/openai/chat/completions` - OpenAI-Format Chat API
  - `/api/v1/openai/models` - Liste verfügbarer Modelle
  - Context-aware Responses mit HA States, Events, Mood
  - Compatible mit Extended OpenAI Conversation HACS

### API Features
- Message history mit HA Context (States, Events, Mood)
- Mood-based response generation
- Habitus pattern integration für intelligentere Antworten
- Ollama-compatible (kann lokal oder cloud-laufen)

### Tests
- Syntax-Check: ✅ openai_chat.py, blueprint.py kompilieren

---

## [0.9.1-alpha.7] - 2026-02-17