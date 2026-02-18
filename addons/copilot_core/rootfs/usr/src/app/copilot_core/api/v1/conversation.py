"""
OpenAI-Compatible Conversation API for PilotSuite Core

Provides /v1/chat/completions and /v1/models endpoints compatible with:
- Extended OpenAI Conversation (jekalmin/extended_openai_conversation)
- OpenAI Python SDK (AsyncOpenAI)
- Any OpenAI-compatible client

Integration with HA:
  Base URL: http://<addon-host>:8099/v1
  API Key:  (your auth_token or any non-empty string)
  Model:    lfm2.5-thinking (or any installed Ollama model)

Features:
- Character presets (copilot, butler, energy_manager, security_guard, friendly, minimal)
- Ollama integration for offline AI (lfm2.5-thinking default)
- Selectable model list (lfm2.5-thinking, qwen3:4b, llama3.2:3b, mistral:7b, fixt/home-3b-v3)
- Streaming SSE support
- Token-based authentication
- Rate limiting
- User habit/context injection for individualization
"""

from flask import Blueprint, request, jsonify, Response
import logging
import json
import os
import threading
import time

import requests as http_requests

from copilot_core.api.security import require_token

logger = logging.getLogger(__name__)

# Two blueprints: /chat/* (legacy) and /v1/* (OpenAI-compatible)
conversation_bp = Blueprint('conversation', __name__, url_prefix='/chat')
openai_compat_bp = Blueprint('openai_compat', __name__, url_prefix='/v1')


# ---------------------------------------------------------------------------
# Recommended models for Home Assistant (selectable in config)
# ---------------------------------------------------------------------------

RECOMMENDED_MODELS = [
    {
        "id": "lfm2.5-thinking",
        "name": "LFM 2.5 Thinking (1.2B)",
        "size_mb": 731,
        "description": "Liquid AI reasoning model. Ultra-light (731MB), 125K context. Good for simple HA control.",
        "tags": ["default", "lightweight", "reasoning"],
    },
    {
        "id": "qwen3:4b",
        "name": "Qwen 3 (4B)",
        "size_mb": 2500,
        "description": "Excellent tool/function calling. Best balance of speed and capability for HA.",
        "tags": ["recommended", "tool-calling"],
    },
    {
        "id": "llama3.2:3b",
        "name": "Llama 3.2 (3B)",
        "size_mb": 2000,
        "description": "Meta's small model with native tool calling. Fast inference, low resource usage.",
        "tags": ["tool-calling", "lightweight"],
    },
    {
        "id": "mistral:7b",
        "name": "Mistral (7B)",
        "size_mb": 4000,
        "description": "Proven function-calling reliability. Widely used in HA community.",
        "tags": ["reliable", "tool-calling"],
    },
    {
        "id": "fixt/home-3b-v3",
        "name": "Home 3B v3 (HA-optimized)",
        "size_mb": 2000,
        "description": "Purpose-trained for HA device control. 97% function-calling accuracy. Use with home-llm.",
        "tags": ["ha-optimized", "tool-calling"],
    },
]

DEFAULT_MODEL = "lfm2.5-thinking"


# ---------------------------------------------------------------------------
# MCP Tools (lazy-loaded to avoid import errors at module level)
# ---------------------------------------------------------------------------

_mcp_tools = None
_mcp_tools_lock = threading.Lock()


def _get_mcp_tools():
    """Lazy-load MCP tools -- avoids crash if mcp_tools module is unavailable."""
    global _mcp_tools
    if _mcp_tools is not None:
        return _mcp_tools
    with _mcp_tools_lock:
        if _mcp_tools is not None:
            return _mcp_tools
        try:
            from copilot_core.mcp_tools import HA_TOOLS, get_openai_functions
            _mcp_tools = {
                "tools": [t.to_dict() for t in HA_TOOLS],
                "functions": get_openai_functions(),
            }
        except Exception:
            logger.warning("MCP tools not available -- conversation will work without function calling")
            _mcp_tools = {"tools": [], "functions": []}
        return _mcp_tools


# ---------------------------------------------------------------------------
# Rate Limiting (simple token-bucket per process)
# ---------------------------------------------------------------------------

_rate_limit_lock = threading.Lock()
_rate_limit_calls: list[float] = []
MAX_CALLS_PER_HOUR = int(os.environ.get("LLM_MAX_CALLS_PER_HOUR", "60"))


def _check_rate_limit() -> bool:
    """Return True if the call is allowed, False if rate-limited."""
    now = time.monotonic()
    with _rate_limit_lock:
        _rate_limit_calls[:] = [t for t in _rate_limit_calls if now - t < 3600]
        if len(_rate_limit_calls) >= MAX_CALLS_PER_HOUR:
            return False
        _rate_limit_calls.append(now)
        return True


# ---------------------------------------------------------------------------
# System prompt for Home Assistant conversation
# ---------------------------------------------------------------------------

HA_SYSTEM_PROMPT = """Du bist PilotSuite CoPilot -- ein lokaler, privacy-first Assistent fuer
Home Assistant Automatisierung.

Du bist Teil der PilotSuite Neural Pipeline:
- Brain Graph erkennt Entity-Beziehungen
- Habitus Miner findet A->B Muster (Support/Confidence/Lift)
- Mood Engine bewertet Comfort/Joy/Frugality
- 12+ Neurons liefern Kontext (Energy, Weather, Presence, UniFi...)

Regeln:
- Du SCHLAEGST VOR, du FUEHRST NICHT AUS ohne Bestaetigung.
- Du erklaerst WARUM, nicht nur WAS.
- Bei Unsicherheit sage "Ich bin mir nicht sicher".
- Antworte auf Deutsch, ausser der User schreibt auf Englisch.
- Keine medizinischen oder gesundheitlichen Aussagen.
- Respektiere Quiet Hours und Guest Mode.
- Beruecksichtige Nutzerpraeferenzen und Gewohnheiten bei Vorschlaegen."""


# ---------------------------------------------------------------------------
# Character Presets for Conversation
# ---------------------------------------------------------------------------

CONVERSATION_CHARACTERS = {
    "copilot": {
        "name": "CoPilot",
        "description": "Der Haupt-Assistent -- hilfsbereit, smart, schlaegt Automatisierungen vor",
        "description_en": "Main assistant -- helpful, smart, suggests automations",
        "system_prompt": HA_SYSTEM_PROMPT,
        "icon": "mdi:brain",
    },
    "butler": {
        "name": "Butler",
        "description": "Formal, aufmerksam, serviceorientiert",
        "description_en": "Formal, attentive, service-oriented",
        "system_prompt": """Du bist ein formeller Butler fuer ein Smart Home.

Dein Stil:
- Hoefliche und formelle Sprache
- Beduerfnisse antizipieren bevor gefragt wird
- Diskret und respektvoll
- Verwende Formulierungen wie "Darf ich..." und "Sehr wohl"

Du steuerst Home Assistant Geraete. Fuehre Anfragen prompt aus und bestaetige formal.
Beruecksichtige die Gewohnheiten der Bewohner bei deinen Empfehlungen.""",
        "icon": "mdi:account-tie",
    },
    "energy_manager": {
        "name": "Energiemanager",
        "description": "Fokus auf Energieeffizienz und Einsparungen",
        "description_en": "Focus on energy efficiency and savings",
        "system_prompt": """Du bist ein Energiemanager fuer ein Smart Home, fokussiert auf Effizienz.

Deine Prioritaeten:
- Energieverbrauch ueberwachen und analysieren
- Sparmoeglichkeiten vorschlagen basierend auf Nutzungsmustern
- Ineffiziente Muster aufzeigen (z.B. Licht an bei Abwesenheit)
- Optimale Zeitplaene empfehlen (guenstige Tarife, PV-Ueberschuss)
- Solar/Batterie-Nutzung optimieren wenn verfuegbar

Beruecksichtige immer die Energieauswirkung bei Befehlen.
Schlage Energiespar-Automatisierungen vor bei Verschwendung.
Nutze die Habitus-Muster um wiederkehrende Verschwendung zu erkennen.""",
        "icon": "mdi:lightning-bolt",
    },
    "security_guard": {
        "name": "Sicherheitswache",
        "description": "Sicherheitsfokussiert, warnt bei Anomalien",
        "description_en": "Security-focused, warns about anomalies",
        "system_prompt": """Du bist ein sicherheitsfokussierter Smart Home Assistent.

Deine Prioritaeten:
- Sicherheitssensoren und Kameras ueberwachen
- Bei ungewoehnlicher Aktivitaet warnen
- Tuer-/Fensterzustaende pruefen
- Alle Sensoren nachts verifizieren
- Abwesenheitsmodus vorschlagen wenn niemand zuhause
- Kinder-Sicherheit priorisieren (Haushaltsprofil beachten)

Sei wachsam. Melde Anomalien. Bestaetige sicherheitsrelevante Aktionen.
Nutze Praesenz- und Bewegungssensoren fuer Kontext.""",
        "icon": "mdi:shield-home",
    },
    "friendly": {
        "name": "Freundlicher Assistent",
        "description": "Laessig, warm, gespraechig",
        "description_en": "Casual, warm, conversational",
        "system_prompt": """Du bist ein freundlicher, laessiger Smart Home Kumpel.

Dein Stil:
- Entspannt und gespraechig
- Lockere Sprache, duzt den Nutzer
- Freundlich und nahbar
- Kurze Unterhaltungen, auch Smalltalk
- Emojis sind ok

Hilf einfach und fuehre nette Gespraeche! Halte Antworten kurz und natuerlich.
Merke dir was der Nutzer mag und beziehe dich darauf.""",
        "icon": "mdi:emoticon-happy",
    },
    "minimal": {
        "name": "Minimal",
        "description": "Kurz, direkt, effizient",
        "description_en": "Short, direct, efficient",
        "system_prompt": """Du bist ein minimaler, effizienter Smart Home Assistent.

Dein Stil:
- Antworten sehr kurz halten (1-2 Saetze max)
- Nur das Noetige sagen
- Direkt zum Punkt
- Kein Smalltalk

Fuehre Befehle effizient aus. Bestaetige mit minimalen Worten wie "Erledigt", "An", "Aus".""",
        "icon": "mdi:text-short",
    },
}

DEFAULT_CHARACTER = "copilot"


# ---------------------------------------------------------------------------
# User context injection (habit data for individualization)
# ---------------------------------------------------------------------------

def _get_user_context() -> str:
    """Build user context string from PilotSuite services for LLM injection.

    Pulls data from MoodService, NeuronManager, and HouseholdProfile
    to give the LLM situational awareness about the home state.
    """
    context_parts = []

    try:
        from copilot_core.mood.service import MoodService
        # Try to get mood service from the app context
        from flask import current_app
        services = current_app.config.get("COPILOT_SERVICES", {})

        # Mood data
        mood_svc = services.get("mood_service")
        if mood_svc:
            summary = mood_svc.get_summary()
            if summary.get("zones", 0) > 0:
                context_parts.append(
                    f"Aktuelle Stimmung: Comfort={summary['average_comfort']:.1f}, "
                    f"Joy={summary['average_joy']:.1f}, "
                    f"Frugality={summary['average_frugality']:.1f} "
                    f"({summary['zones']} Zonen, {summary['zones_with_media']} mit Medien)"
                )

        # Neuron pipeline data
        neuron_mgr = services.get("neuron_manager")
        if neuron_mgr:
            mood_sum = neuron_mgr.get_mood_summary()
            if mood_sum.get("mood") != "unknown":
                context_parts.append(
                    f"Neural-Pipeline Stimmung: {mood_sum['mood']} "
                    f"(Confidence: {mood_sum.get('confidence', 0):.1f})"
                )

        # Household data
        household = services.get("household_profile")
        if household:
            hh = household.to_dict()
            context_parts.append(
                f"Haushalt: {hh.get('adults', 0)} Erwachsene, "
                f"{hh.get('children', 0)} Kinder"
            )

        # Brain graph quick stats
        bg_svc = services.get("brain_graph_service")
        if bg_svc:
            stats = bg_svc.get_stats()
            if stats.get("node_count", 0) > 0:
                context_parts.append(
                    f"Brain Graph: {stats['node_count']} Nodes, "
                    f"{stats.get('edge_count', 0)} Edges"
                )

    except Exception as exc:
        logger.debug("Could not load user context: %s", exc)

    if not context_parts:
        return ""

    return "\n\nAktueller Kontext:\n" + "\n".join(f"- {p}" for p in context_parts)


# ---------------------------------------------------------------------------
# OpenAI-compatible /v1/models endpoint (required by extended_openai_conversation)
# ---------------------------------------------------------------------------

@openai_compat_bp.route('/models', methods=['GET'])
def list_models():
    """OpenAI-compatible model listing. Required by extended_openai_conversation for validation."""
    ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    models = []

    # Try to get installed models from Ollama
    try:
        resp = http_requests.get(f"{ollama_url}/api/tags", timeout=5)
        if resp.status_code == 200:
            for m in resp.json().get("models", []):
                name = m.get("name", "")
                models.append({
                    "id": name,
                    "object": "model",
                    "created": int(m.get("modified_at", time.time())),
                    "owned_by": "ollama",
                })
    except Exception:
        pass

    # Always include the configured default even if Ollama is down
    configured_model = os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)
    if not any(m["id"] == configured_model for m in models):
        models.insert(0, {
            "id": configured_model,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "ollama",
        })

    return jsonify({
        "object": "list",
        "data": models,
    })


@openai_compat_bp.route('/models/<path:model_id>', methods=['GET'])
def get_model(model_id):
    """OpenAI-compatible single model retrieval."""
    return jsonify({
        "id": model_id,
        "object": "model",
        "created": int(time.time()),
        "owned_by": "ollama",
    })


# ---------------------------------------------------------------------------
# OpenAI-compatible /v1/chat/completions endpoint
# ---------------------------------------------------------------------------

@openai_compat_bp.route('/chat/completions', methods=['POST'])
@require_token
def openai_chat_completions():
    """OpenAI-compatible chat completions at /v1/chat/completions.

    This is the primary endpoint for extended_openai_conversation integration.
    """
    return _handle_chat_completions()


# Legacy /chat/completions (kept for backwards compatibility)
@conversation_bp.route('/completions', methods=['POST'])
@require_token
def chat_completions():
    """Legacy chat completions endpoint at /chat/completions."""
    return _handle_chat_completions()


def _handle_chat_completions():
    """Shared handler for both /v1/chat/completions and /chat/completions."""
    if not _check_rate_limit():
        return jsonify({
            "error": {
                "message": "Rate limit exceeded",
                "type": "rate_limit_error",
                "code": "rate_limit_exceeded",
            }
        }), 429

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": {"message": "No JSON body provided", "type": "invalid_request_error"}}), 400

        messages = data.get('messages', [])
        stream = data.get('stream', False)
        model_override = data.get('model')
        temperature = data.get('temperature')
        max_tokens = data.get('max_tokens') or data.get('max_completion_tokens')

        # Extract last user message for logging
        user_message = ""
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                user_message = msg.get('content', '')
                break

        if not messages:
            return jsonify({"error": {"message": "No messages provided", "type": "invalid_request_error"}}), 400

        logger.info("Chat request: %s...", user_message[:80] if user_message else "(system-only)")

        response = _process_conversation(messages, model_override=model_override,
                                         temperature=temperature, max_tokens=max_tokens)

        if stream:
            return _stream_response(response)

        return jsonify(response)

    except Exception as exc:
        logger.exception("Error in chat completions")
        return jsonify({"error": {"message": str(exc), "type": "server_error"}}), 500


# ---------------------------------------------------------------------------
# Additional /chat/* endpoints
# ---------------------------------------------------------------------------

@conversation_bp.route('/tools', methods=['GET'])
@require_token
def list_tools():
    """List available MCP tools for function calling."""
    tools = _get_mcp_tools()
    return jsonify({
        "tools": tools["tools"],
        "count": len(tools["tools"]),
    })


@conversation_bp.route('/characters', methods=['GET'])
def list_characters():
    """List available conversation characters."""
    return jsonify({
        "characters": [
            {
                "id": key,
                "name": val["name"],
                "description": val["description"],
                "description_en": val.get("description_en", ""),
                "icon": val.get("icon", "mdi:robot"),
            }
            for key, val in CONVERSATION_CHARACTERS.items()
        ],
        "default": DEFAULT_CHARACTER,
    })


@conversation_bp.route('/models/recommended', methods=['GET'])
def list_recommended_models():
    """List recommended Ollama models for Home Assistant use."""
    ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    current_model = os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)

    # Check which models are installed
    installed = set()
    try:
        resp = http_requests.get(f"{ollama_url}/api/tags", timeout=5)
        if resp.status_code == 200:
            for m in resp.json().get("models", []):
                installed.add(m.get("name", "").split(":")[0])
    except Exception:
        pass

    models = []
    for m in RECOMMENDED_MODELS:
        models.append({
            **m,
            "installed": m["id"].split(":")[0] in installed or m["id"] in installed,
            "active": m["id"] == current_model,
        })

    return jsonify({
        "models": models,
        "current_model": current_model,
        "ollama_url": ollama_url,
    })


@conversation_bp.route('/status', methods=['GET'])
def llm_status():
    """Return LLM availability and configuration."""
    ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    ollama_model = os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)
    available = False
    installed_models = []

    try:
        resp = http_requests.get(f"{ollama_url}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            installed_models = [m.get("name", "") for m in models]
            available = any(m.startswith(ollama_model) for m in installed_models)
    except Exception:
        pass

    now = time.monotonic()
    with _rate_limit_lock:
        calls_this_hour = len([t for t in _rate_limit_calls if now - t < 3600])

    return jsonify({
        "available": available,
        "model": ollama_model,
        "provider": "ollama",
        "ollama_url": ollama_url,
        "installed_models": installed_models,
        "calls_this_hour": calls_this_hour,
        "max_calls_per_hour": MAX_CALLS_PER_HOUR,
        "characters": list(CONVERSATION_CHARACTERS.keys()),
        "integration_url": f"http://[HOST]:8099/v1",
        "integration_hint": "Use base_url=http://<addon-host>:8099/v1 in extended_openai_conversation",
    })


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _process_conversation(messages: list, model_override: str = None,
                          temperature: float = None, max_tokens: int = None) -> dict:
    """Process conversation through Ollama.

    Handles character selection, user context injection, and Ollama API calls.
    """
    ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    ollama_model = model_override or os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)
    timeout = int(os.environ.get("LLM_TIMEOUT", "120"))

    # Resolve character
    character_name = os.environ.get("CONVERSATION_CHARACTER", DEFAULT_CHARACTER)
    for char_key in CONVERSATION_CHARACTERS:
        if char_key in ollama_model.lower():
            character_name = char_key
            break

    character = CONVERSATION_CHARACTERS.get(character_name, CONVERSATION_CHARACTERS[DEFAULT_CHARACTER])

    # Build system prompt with user context injection
    system_prompt = character["system_prompt"]
    user_context = _get_user_context()
    if user_context:
        system_prompt += user_context

    logger.info("Using character: %s (%s), model: %s", character_name, character['name'], ollama_model)

    # Build Ollama messages -- inject our system prompt, keep conversation history
    ollama_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages:
        role = msg.get("role", "user")
        if role != "system":
            ollama_messages.append({"role": role, "content": msg.get("content", "")})

    # Build Ollama request options
    ollama_options = {}
    if temperature is not None:
        ollama_options["temperature"] = temperature
    if max_tokens is not None:
        ollama_options["num_predict"] = max_tokens

    response_content = ""
    try:
        payload = {
            "model": ollama_model,
            "messages": ollama_messages,
            "stream": False,
        }
        if ollama_options:
            payload["options"] = ollama_options

        resp = http_requests.post(
            f"{ollama_url}/api/chat",
            json=payload,
            timeout=timeout,
        )
        if resp.status_code == 200:
            result = resp.json()
            response_content = result.get("message", {}).get("content", "")
        else:
            logger.warning("Ollama returned %s: %s", resp.status_code, resp.text[:200])
            response_content = _fallback_response(ollama_url, ollama_model)
    except http_requests.exceptions.ConnectionError:
        logger.error("Could not connect to Ollama at %s", ollama_url)
        response_content = _offline_fallback(ollama_url, ollama_model)
    except http_requests.exceptions.Timeout:
        logger.error("Ollama timeout after %ds", timeout)
        response_content = f"Timeout nach {timeout}s. Das Modell braucht zu lange -- pruefe Ollama und Modellgroesse."
    except Exception:
        logger.exception("Error calling Ollama")
        response_content = _fallback_response(ollama_url, ollama_model)

    return {
        "id": f"chatcmpl-{os.urandom(12).hex()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": ollama_model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": response_content},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": sum(len(m.get("content", "")) for m in ollama_messages),
            "completion_tokens": len(response_content),
            "total_tokens": sum(len(m.get("content", "")) for m in ollama_messages) + len(response_content),
        },
    }


def _fallback_response(url: str, model: str) -> str:
    return (
        f"Ollama ist nicht erreichbar ({url}, Modell: {model}). "
        "Bitte pruefe ob Ollama laeuft und das Modell installiert ist."
    )


def _offline_fallback(url: str, model: str) -> str:
    return (
        f"Ich bin offline. Ollama unter {url} mit Modell {model} nicht erreichbar. "
        "Bitte pruefe die Addon-Konfiguration."
    )


def _stream_response(response: dict):
    """OpenAI-compatible SSE streaming implementation."""
    model = response.get("model", DEFAULT_MODEL)
    response_id = response.get("id", f"chatcmpl-{os.urandom(12).hex()}")

    def generate():
        content = response["choices"][0]["message"]["content"]
        # Stream word by word for natural feel
        words = content.split()
        for i, word in enumerate(words):
            chunk = {
                "id": response_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {"content": word + (" " if i < len(words) - 1 else "")},
                    "finish_reason": None,
                }],
            }
            yield f"data: {json.dumps(chunk)}\n\n"

        # Final chunk with finish_reason
        final = {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        yield f"data: {json.dumps(final)}\n\n"
        yield "data: [DONE]\n\n"

    return Response(generate(), mimetype='text/event-stream',
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def register_routes(app):
    """Register conversation routes with Flask app."""
    app.register_blueprint(conversation_bp)
    app.register_blueprint(openai_compat_bp)
    logger.info("Registered conversation API at /chat/* and /v1/*")
