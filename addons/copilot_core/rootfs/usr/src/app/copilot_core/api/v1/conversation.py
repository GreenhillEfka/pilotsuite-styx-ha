"""
OpenAI-Compatible Conversation API for PilotSuite Core

Provides /v1/chat/completions and /v1/models endpoints compatible with:
- Extended OpenAI Conversation (jekalmin/extended_openai_conversation)
- OpenAI Python SDK (AsyncOpenAI)
- Any OpenAI-compatible client (incl. OpenClaw)

Integration with HA:
  Base URL: http://<addon-host>:8909/v1
  API Key:  (your auth_token or any non-empty string)
  Model:    qwen3:4b (default, best tool-calling) or any installed Ollama model

LLM Provider Chain:
  1. Ollama (local, default, privacy-first)
  2. Cloud API fallback (OpenClaw, OpenAI, any /v1/ endpoint)
  Config: prefer_local=true tries Ollama first, falls back to cloud

Features:
- Character presets (copilot, butler, energy_manager, security_guard, friendly, minimal)
- Ollama + Cloud fallback for offline/online AI
- Tool-calling with server-side HA execution (9 tools)
- Selectable models (qwen3:4b, qwen3:0.6b, lfm2.5-thinking, llama3.2:3b, mistral:7b)
- Streaming SSE support
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
from copilot_core.llm_provider import LLMProvider

logger = logging.getLogger(__name__)

# Singleton LLM provider (thread-safe via GIL for reads)
_llm_provider = None
_llm_provider_lock = threading.Lock()


def _get_llm_provider() -> LLMProvider:
    global _llm_provider
    if _llm_provider is not None:
        return _llm_provider
    with _llm_provider_lock:
        if _llm_provider is not None:
            return _llm_provider
        _llm_provider = LLMProvider()
        return _llm_provider

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
        "description": "Liquid AI reasoning model. Ultra-light (731MB), 32K context. Good for simple conversation.",
        "tags": ["default", "lightweight", "reasoning"],
        "supports_tools": False,
    },
    {
        "id": "qwen3:4b",
        "name": "Qwen 3 (4B)",
        "size_mb": 2500,
        "description": "Best for tool-calling (score 0.88). Native MCP support. Recommended for HA control.",
        "tags": ["recommended", "tool-calling"],
        "supports_tools": True,
    },
    {
        "id": "qwen3:0.6b",
        "name": "Qwen 3 (0.6B)",
        "size_mb": 400,
        "description": "Ultra-lightweight with tool-calling (score 0.88). Smallest capable model.",
        "tags": ["ultra-lightweight", "tool-calling"],
        "supports_tools": True,
    },
    {
        "id": "llama3.2:3b",
        "name": "Llama 3.2 (3B)",
        "size_mb": 2000,
        "description": "Meta's small model. 128K context window. Basic tool calling support.",
        "tags": ["tool-calling", "lightweight"],
        "supports_tools": True,
    },
    {
        "id": "mistral:7b",
        "name": "Mistral (7B)",
        "size_mb": 4000,
        "description": "Proven function-calling reliability. Widely used in HA community.",
        "tags": ["reliable", "tool-calling"],
        "supports_tools": True,
    },
    {
        "id": "fixt/home-3b-v3",
        "name": "Home 3B v3 (HA-optimized)",
        "size_mb": 2000,
        "description": "Purpose-trained for HA device control. 97% function-calling accuracy. Use with home-llm.",
        "tags": ["ha-optimized", "tool-calling"],
        "supports_tools": True,
    },
]

DEFAULT_MODEL = "qwen3:4b"


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

ASSISTANT_NAME = os.environ.get("ASSISTANT_NAME", "Styx")

HA_SYSTEM_PROMPT_TEMPLATE = """Du bist {name} -- der lokale, privacy-first KI-Assistent der PilotSuite
fuer Home Assistant. Dein Name ist {name} und du bist die Verbindung zwischen der
digitalen Smart-Home-Welt und dem Zuhause der Bewohner.

Du bist Teil der PilotSuite Neural Pipeline:
- Brain Graph erkennt Entity-Beziehungen und visualisiert sie als neuronales Netz
- Habitus Miner findet A->B Verhaltensmuster (Support/Confidence/Lift)
- Mood Engine bewertet Comfort/Joy/Frugality pro Zone
- 14+ Neurons liefern Kontext (Energy, Weather, Presence, UniFi, Camera, Media...)
- Conversation Memory speichert dein Langzeitgedaechtnis

Faehigkeiten:
- Du kannst Geraete steuern (Lichter, Schalter, Klima, Szenen, etc.)
- Du kannst AUTOMATIONEN ERSTELLEN wenn der User z.B. sagt:
  "Wenn die Kaffeemaschine einschaltet, schalte die Kaffeemuehle ein"
  Nutze dafuer das pilotsuite.create_automation Tool mit strukturierten Triggern und Aktionen.
  Frage den User nach der genauen Entity-ID wenn noetig (z.B. switch.coffee_machine).
- Du kannst erstellte Automationen auflisten (pilotsuite.list_automations)
- Du kannst Entity-Zustaende abfragen, Historie einsehen, Wetter vorhersagen, etc.
- Du kannst das WEB DURCHSUCHEN (pilotsuite.web_search) fuer aktuelle Informationen,
  Recherche, Produktvergleiche, Anleitungen, etc.
- Du kannst AKTUELLE NACHRICHTEN laden (pilotsuite.get_news) von Tagesschau, Spiegel etc.
- Du kannst REGIONALE WARNUNGEN abrufen (pilotsuite.get_warnings) -- NINA/BBK Zivilschutz
  und DWD Wetterwarnungen fuer die Region.
- Du kannst MEDIA ZONEN steuern (pilotsuite.play_zone) -- Musik/Video in Habituszonen
  abspielen, pausieren, Lautstaerke einstellen.
- Du kannst die MUSIKWOLKE starten (pilotsuite.musikwolke) -- Musik folgt dem User
  durch die Raeume. Sage z.B. "Musik soll mir folgen" oder "Musikwolke starten".

Modul-Zustaende (Autonomie-System):
- active: Vorschlaege werden AUTOMATISCH umgesetzt (wenn BEIDE Module aktiv sind)
- learning: Daten sammeln + Vorschlaege zur MANUELLEN Uebernahme erzeugen
- off: Modul deaktiviert

Regeln:
- Wenn beide beteiligte Module AKTIV sind: Du FUEHRST AUS und informierst den User.
- Wenn mindestens ein Modul im LEARNING ist: Du SCHLAEGST VOR und wartest auf Bestaetigung.
- Du erklaerst WARUM, nicht nur WAS.
- Bei Unsicherheit sage "Ich bin mir nicht sicher".
- Antworte auf Deutsch, ausser der User schreibt auf Englisch.
- Keine medizinischen oder gesundheitlichen Aussagen.
- Respektiere Quiet Hours und Guest Mode.
- Beruecksichtige Nutzerpraeferenzen und Gewohnheiten bei Vorschlaegen.
- Stelle dich bei der ersten Nachricht kurz als {name} vor."""

HA_SYSTEM_PROMPT = HA_SYSTEM_PROMPT_TEMPLATE.format(name=ASSISTANT_NAME)


# ---------------------------------------------------------------------------
# Character Presets for Conversation
# ---------------------------------------------------------------------------

CONVERSATION_CHARACTERS = {
    "copilot": {
        "name": ASSISTANT_NAME,
        "description": f"{ASSISTANT_NAME} -- die Verbindung beider Welten, hilfsbereit und smart",
        "description_en": f"{ASSISTANT_NAME} -- connecting both worlds, helpful and smart",
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

        # Habitus patterns (recent discoveries)
        habitus_svc = services.get("habitus_service")
        if habitus_svc:
            recent = habitus_svc.list_recent_patterns(limit=3)
            if recent:
                pattern_lines = []
                for p in recent:
                    meta = p.get("metadata", {})
                    ant = meta.get("antecedent", {}).get("full", "?")
                    cons = meta.get("consequent", {}).get("full", "?")
                    pattern_lines.append(f"{ant} -> {cons}")
                context_parts.append("Erkannte Muster: " + "; ".join(pattern_lines))

        # Conversation memory: learned preferences
        conv_memory = services.get("conversation_memory")
        if conv_memory:
            pref_context = conv_memory.get_preferences_for_prompt()
            if pref_context:
                context_parts.append(pref_context)

        # Regional warnings (v3.1.0)
        ws = services.get("web_search_service")
        if ws:
            try:
                summary = ws.get_warning_summary()
                if summary:
                    context_parts.append(f"Regionale Warnungen: {summary}")
            except Exception:
                pass

        # Active Musikwolke sessions (v3.1.0)
        media_mgr = services.get("media_zone_manager")
        if media_mgr:
            try:
                sessions = media_mgr.get_musikwolke_sessions()
                if sessions:
                    context_parts.append(
                        f"Musikwolke aktiv: {len(sessions)} Session(s)"
                    )
            except Exception:
                pass

        # Waste collection context (v3.2.0)
        waste_svc = services.get("waste_service")
        if waste_svc:
            try:
                waste_ctx = waste_svc.get_context_for_llm()
                if waste_ctx:
                    context_parts.append(waste_ctx)
            except Exception:
                pass

        # Birthday context (v3.2.0)
        birthday_svc = services.get("birthday_service")
        if birthday_svc:
            try:
                bday_ctx = birthday_svc.get_context_for_llm()
                if bday_ctx:
                    context_parts.append(bday_ctx)
            except Exception:
                pass

        # Entity tags context (v3.2.3)
        tag_registry = services.get("tag_registry")
        if tag_registry and hasattr(tag_registry, "get_context_for_llm"):
            try:
                tags_ctx = tag_registry.get_context_for_llm()
                if tags_ctx:
                    context_parts.append(tags_ctx)
            except Exception:
                pass

        # Presence context (v3.3.0)
        try:
            from copilot_core.api.v1.presence import get_presence_context_for_llm
            presence_ctx = get_presence_context_for_llm()
            if presence_ctx:
                context_parts.append(presence_ctx)
        except Exception:
            pass

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
        tools = data.get('tools')  # Client-specified tools (e.g. from extended_openai_conversation)

        # Extract last user message for logging
        user_message = ""
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                user_message = msg.get('content', '')
                break

        if not messages:
            return jsonify({"error": {"message": "No messages provided", "type": "invalid_request_error"}}), 400

        logger.info("Chat request: %s...", user_message[:80] if user_message else "(system-only)")

        # Store user message in conversation memory (lifelong learning)
        _store_in_memory(user_message, role="user")

        response = _process_conversation(messages, model_override=model_override,
                                         temperature=temperature, max_tokens=max_tokens,
                                         tools=tools)

        # Store assistant response in memory (only for text, not tool_calls)
        choice = response.get("choices", [{}])[0]
        if choice.get("finish_reason") != "tool_calls":
            assistant_content = choice.get("message", {}).get("content", "")
            if assistant_content:
                _store_in_memory(assistant_content, role="assistant")

        # If tool_calls response, return directly (no streaming)
        if choice.get("finish_reason") == "tool_calls":
            return jsonify(response)

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
    provider = _get_llm_provider()
    provider_status = provider.status()

    # Also check installed Ollama models
    installed_models = []
    try:
        resp = http_requests.get(f"{provider_status['ollama_url']}/api/tags", timeout=5)
        if resp.status_code == 200:
            installed_models = [m.get("name", "") for m in resp.json().get("models", [])]
    except Exception:
        pass

    now = time.monotonic()
    with _rate_limit_lock:
        calls_this_hour = len([t for t in _rate_limit_calls if now - t < 3600])

    return jsonify({
        "available": provider_status["ollama_available"] or provider_status["cloud_configured"],
        "model": provider_status["ollama_model"],
        "active_provider": provider_status["active_provider"],
        "prefer_local": provider_status["prefer_local"],
        "ollama_url": provider_status["ollama_url"],
        "ollama_available": provider_status["ollama_available"],
        "cloud_configured": provider_status["cloud_configured"],
        "cloud_api_url": provider_status["cloud_api_url"],
        "cloud_model": provider_status["cloud_model"],
        "installed_models": installed_models,
        "calls_this_hour": calls_this_hour,
        "max_calls_per_hour": MAX_CALLS_PER_HOUR,
        "assistant_name": ASSISTANT_NAME,
        "version": os.environ.get("COPILOT_VERSION", "1.1.0"),
        "character": os.environ.get("CONVERSATION_CHARACTER", "copilot"),
        "characters": list(CONVERSATION_CHARACTERS.keys()),
        "integration_url": "http://[HOST]:8909/v1",
        "integration_hint": "Use base_url=http://<addon-host>:8909/v1 in extended_openai_conversation or OpenClaw",
    })


@conversation_bp.route('/memory', methods=['GET'])
def memory_stats():
    """Return conversation memory statistics."""
    try:
        from flask import current_app
        services = current_app.config.get("COPILOT_SERVICES", {})
        conv_memory = services.get("conversation_memory")
        if conv_memory:
            stats = conv_memory.get_stats()
            prefs = conv_memory.get_user_preferences()
            return jsonify({
                "stats": stats,
                "preferences": [
                    {"key": p.key, "value": p.value, "confidence": p.confidence,
                     "source": p.source, "mentions": p.mention_count}
                    for p in prefs
                ],
            })
        return jsonify({"stats": {}, "preferences": [], "message": "Memory not initialized"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@conversation_bp.route('/memory/preferences', methods=['GET'])
def memory_preferences():
    """Return learned user preferences."""
    try:
        from flask import current_app
        services = current_app.config.get("COPILOT_SERVICES", {})
        conv_memory = services.get("conversation_memory")
        if conv_memory:
            prefs = conv_memory.get_user_preferences()
            return jsonify({
                "preferences": [
                    {"key": p.key, "value": p.value, "confidence": p.confidence,
                     "source": p.source, "mentions": p.mention_count}
                    for p in prefs
                ],
            })
        return jsonify({"preferences": []})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


def _store_in_memory(content: str, role: str = "user"):
    """Store a message in conversation memory (fire-and-forget)."""
    try:
        from flask import current_app
        services = current_app.config.get("COPILOT_SERVICES", {})
        conv_memory = services.get("conversation_memory")
        if conv_memory and content:
            character = os.environ.get("CONVERSATION_CHARACTER", DEFAULT_CHARACTER)
            conv_memory.store_message(role=role, content=content, character=character)
    except Exception:
        logger.debug("Could not store message in memory", exc_info=True)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _process_conversation(messages: list, model_override: str = None,
                          temperature: float = None, max_tokens: int = None,
                          tools: list = None) -> dict:
    """Process conversation through LLM provider (Ollama -> Cloud fallback).

    Handles character selection, user context injection, and LLM calls.
    When ``tools`` are provided, the LLM may return ``tool_calls`` instead of text.
    """
    provider = _get_llm_provider()
    model = model_override or provider.active_model

    # Resolve character
    character_name = os.environ.get("CONVERSATION_CHARACTER", DEFAULT_CHARACTER)
    for char_key in CONVERSATION_CHARACTERS:
        if char_key in model.lower():
            character_name = char_key
            break

    character = CONVERSATION_CHARACTERS.get(character_name, CONVERSATION_CHARACTERS[DEFAULT_CHARACTER])

    # Build system prompt with user context injection
    system_prompt = character["system_prompt"]
    user_context = _get_user_context()
    if user_context:
        system_prompt += user_context

    logger.info("Using character: %s (%s), model: %s", character_name, character['name'], model)

    # Build LLM messages -- inject our system prompt, keep conversation history
    llm_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages:
        role = msg.get("role", "user")
        if role != "system":
            entry = {"role": role, "content": msg.get("content", "")}
            if msg.get("tool_calls"):
                entry["tool_calls"] = msg["tool_calls"]
            if msg.get("tool_call_id"):
                entry["tool_call_id"] = msg["tool_call_id"]
            llm_messages.append(entry)

    # Call LLM provider (handles Ollama -> Cloud fallback)
    result = provider.chat(
        messages=llm_messages, tools=tools,
        model=model, temperature=temperature, max_tokens=max_tokens,
    )

    response_content = result.get("content", "")
    raw_tool_calls = result.get("tool_calls")
    used_provider = result.get("provider", "unknown")
    finish_reason = "stop"
    tool_calls_response = None

    if raw_tool_calls:
        finish_reason = "tool_calls"
        tool_calls_response = []
        for tc in raw_tool_calls:
            fn = tc.get("function", {})
            tool_calls_response.append({
                "id": f"call_{os.urandom(12).hex()}",
                "type": "function",
                "function": {
                    "name": fn.get("name", ""),
                    "arguments": json.dumps(fn.get("arguments", {}))
                        if isinstance(fn.get("arguments"), dict)
                        else fn.get("arguments", "{}"),
                },
            })

    response_message = {"role": "assistant", "content": response_content}
    if tool_calls_response:
        response_message["tool_calls"] = tool_calls_response

    return {
        "id": f"chatcmpl-{os.urandom(12).hex()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": response_message,
            "finish_reason": finish_reason,
        }],
        "usage": {
            "prompt_tokens": sum(len(m.get("content", "")) for m in llm_messages),
            "completion_tokens": len(response_content),
            "total_tokens": sum(len(m.get("content", "")) for m in llm_messages) + len(response_content),
        },
        "system_fingerprint": f"pilotsuite-{used_provider}",
    }


# ---------------------------------------------------------------------------
# Server-side tool execution (for Telegram / direct chat)
# ---------------------------------------------------------------------------

MAX_TOOL_ROUNDS = 5


def _execute_ha_tool(name: str, arguments: dict) -> dict:
    """Execute a Home Assistant tool via Supervisor REST API."""
    ha_url = os.environ.get("SUPERVISOR_API", "http://supervisor/core/api")
    ha_token = os.environ.get("SUPERVISOR_TOKEN", "")

    if not ha_token:
        return {"error": "No SUPERVISOR_TOKEN -- HA tools unavailable outside addon"}

    headers = {"Authorization": f"Bearer {ha_token}", "Content-Type": "application/json"}

    try:
        if name == "ha.call_service":
            domain = arguments.get("domain", "")
            service = arguments.get("service", "")
            data = arguments.get("service_data", {})
            target = arguments.get("target")
            if target:
                data["target"] = target
            resp = http_requests.post(
                f"{ha_url}/services/{domain}/{service}", json=data,
                headers=headers, timeout=10,
            )
            return {"success": resp.ok, "data": resp.json() if resp.ok else resp.text[:200]}

        elif name == "ha.get_states":
            entity_id = arguments.get("entity_id")
            if entity_id:
                resp = http_requests.get(f"{ha_url}/states/{entity_id}", headers=headers, timeout=10)
                return resp.json() if resp.ok else {"error": resp.text[:200]}
            resp = http_requests.get(f"{ha_url}/states", headers=headers, timeout=10)
            states = resp.json() if resp.ok else []
            domain_filter = arguments.get("domain")
            if domain_filter:
                states = [s for s in states if s.get("entity_id", "").startswith(f"{domain_filter}.")]
            return {"states": [{"entity_id": s["entity_id"], "state": s["state"]} for s in states[:50]]}

        elif name == "ha.get_history":
            entity_ids = arguments.get("entity_ids", [])
            start = arguments.get("start_time", "")
            params = {"filter_entity_id": ",".join(entity_ids)}
            if arguments.get("end_time"):
                params["end_time"] = arguments["end_time"]
            url = f"{ha_url}/history/period/{start}" if start else f"{ha_url}/history/period"
            resp = http_requests.get(url, params=params, headers=headers, timeout=15)
            return {"history": resp.json() if resp.ok else []}

        elif name == "ha.activate_scene":
            entity_id = arguments.get("entity_id", "")
            resp = http_requests.post(
                f"{ha_url}/services/scene/turn_on", json={"entity_id": entity_id},
                headers=headers, timeout=10,
            )
            return {"success": resp.ok}

        elif name == "ha.get_config":
            resp = http_requests.get(f"{ha_url}/config", headers=headers, timeout=10)
            return resp.json() if resp.ok else {"error": resp.text[:200]}

        elif name == "ha.get_services":
            resp = http_requests.get(f"{ha_url}/services", headers=headers, timeout=10)
            services_list = resp.json() if resp.ok else []
            domain_filter = arguments.get("domain")
            if domain_filter:
                services_list = [s for s in services_list if s.get("domain") == domain_filter]
            return {"services": services_list}

        elif name == "ha.fire_event":
            event_type = arguments.get("event_type", "")
            event_data = arguments.get("event_data", {})
            resp = http_requests.post(
                f"{ha_url}/events/{event_type}", json=event_data,
                headers=headers, timeout=10,
            )
            return {"success": resp.ok}

        elif name == "calendar.get_events":
            calendar_id = arguments.get("calendar_id", "")
            params = {}
            if arguments.get("start_date_time"):
                params["start"] = arguments["start_date_time"]
            if arguments.get("end_date_time"):
                params["end"] = arguments["end_date_time"]
            resp = http_requests.get(
                f"{ha_url}/calendars/{calendar_id}", params=params,
                headers=headers, timeout=10,
            )
            return {"events": resp.json() if resp.ok else []}

        elif name == "weather.get_forecast":
            entity_id = arguments.get("entity_id", "")
            forecast_type = arguments.get("type", "daily")
            resp = http_requests.post(
                f"{ha_url}/services/weather/get_forecasts",
                json={"entity_id": entity_id, "type": forecast_type},
                headers=headers, timeout=10,
            )
            return resp.json() if resp.ok else {"error": resp.text[:200]}

        elif name == "pilotsuite.create_automation":
            return _execute_create_automation(arguments)

        elif name == "pilotsuite.list_automations":
            return _execute_list_automations()

        elif name == "pilotsuite.web_search":
            return _execute_web_search(arguments)

        elif name == "pilotsuite.get_news":
            return _execute_get_news(arguments)

        elif name == "pilotsuite.get_warnings":
            return _execute_get_warnings()

        elif name == "pilotsuite.play_zone":
            return _execute_play_zone(arguments)

        elif name == "pilotsuite.musikwolke":
            return _execute_musikwolke(arguments)

        elif name == "pilotsuite.waste_status":
            return _execute_waste_status()

        elif name == "pilotsuite.birthday_status":
            return _execute_birthday_status()

        else:
            return {"error": f"Unknown tool: {name}"}

    except Exception as exc:
        logger.warning("Tool execution failed (%s): %s", name, exc)
        return {"error": str(exc)}


def _execute_create_automation(args: dict) -> dict:
    """Create a HA automation from structured LLM tool call arguments.

    This bridges the conversation pipeline to the AutomationCreator,
    allowing users to say things like:
      "When the coffee machine turns on, sync the coffee grinder"
    and have it create a real HA automation.
    """
    try:
        from flask import current_app
        services = current_app.config.get("COPILOT_SERVICES", {})
        creator = services.get("automation_creator")
    except Exception:
        creator = None

    # Build structured trigger/action for AutomationCreator
    alias = args.get("alias", "PilotSuite Automation")
    trigger_type = args.get("trigger_type", "state")

    # Build trigger dict directly (bypassing regex parsing)
    trigger = None
    if trigger_type == "state":
        entity = args.get("trigger_entity")
        if not entity:
            return {"error": "trigger_entity is required for state triggers"}
        trigger = {"platform": "state", "entity_id": entity}
        if args.get("trigger_to"):
            trigger["to"] = args["trigger_to"]
        if args.get("trigger_from"):
            trigger["from"] = args["trigger_from"]
    elif trigger_type == "time":
        t = args.get("trigger_time")
        if not t:
            return {"error": "trigger_time is required for time triggers (HH:MM:SS)"}
        trigger = {"platform": "time", "at": t}
    elif trigger_type == "sun":
        event = args.get("trigger_sun_event", "sunset")
        trigger = {"platform": "sun", "event": event}
        if args.get("trigger_sun_offset"):
            trigger["offset"] = args["trigger_sun_offset"]
    elif trigger_type == "numeric_state":
        entity = args.get("trigger_entity")
        if not entity:
            return {"error": "trigger_entity is required for numeric_state triggers"}
        trigger = {"platform": "numeric_state", "entity_id": entity}
        if args.get("trigger_above") is not None:
            trigger["above"] = float(args["trigger_above"])
        if args.get("trigger_below") is not None:
            trigger["below"] = float(args["trigger_below"])
        if "above" not in trigger and "below" not in trigger:
            return {"error": "numeric_state trigger requires trigger_above or trigger_below"}
    else:
        return {"error": f"Unknown trigger_type: {trigger_type}"}

    # Build optional conditions
    conditions = []
    for cond in args.get("conditions", []):
        ctype = cond.get("type")
        if ctype == "numeric_state":
            cd = {"condition": "numeric_state", "entity_id": cond.get("entity_id")}
            if cond.get("above") is not None:
                cd["above"] = float(cond["above"])
            if cond.get("below") is not None:
                cd["below"] = float(cond["below"])
            conditions.append(cd)
        elif ctype == "template":
            conditions.append({
                "condition": "template",
                "value_template": cond.get("value_template", "{{ true }}"),
            })

    # Build action dict
    action_service = args.get("action_service", "")
    action_entity = args.get("action_entity", "")
    if not action_service or not action_entity:
        return {"error": "action_service and action_entity are required"}

    action = {"service": action_service, "target": {"entity_id": action_entity}}
    if args.get("action_data"):
        action["data"] = args["action_data"]

    # Post directly to HA Supervisor API (structured, no regex needed)
    ha_url = os.environ.get("SUPERVISOR_API", "http://supervisor/core/api")
    ha_token = os.environ.get("SUPERVISOR_TOKEN", "")

    if not ha_token:
        return {"error": "No SUPERVISOR_TOKEN -- cannot create automations outside HA add-on"}

    import uuid
    automation_id = f"styx_{uuid.uuid4().hex[:12]}"
    config = {
        "id": automation_id,
        "alias": alias,
        "description": f"Created by PilotSuite Styx via conversation.",
        "trigger": [trigger],
        "action": [action],
        "mode": "single",
        "tags": ["pilotsuite_styx"],
    }
    if conditions:
        config["condition"] = conditions

    headers = {"Authorization": f"Bearer {ha_token}", "Content-Type": "application/json"}
    try:
        resp = http_requests.post(
            f"{ha_url}/config/automation/config/{automation_id}",
            json=config, headers=headers, timeout=15,
        )
        if resp.ok:
            # Also record in AutomationCreator if available
            if creator:
                try:
                    creator._created.append({
                        "automation_id": automation_id,
                        "alias": alias,
                        "created_at": time.time(),
                        "antecedent": json.dumps(trigger),
                        "consequent": json.dumps(action),
                    })
                except Exception:
                    pass

            logger.info("Automation created via conversation: %s (%s)", automation_id, alias)
            return {
                "success": True,
                "automation_id": automation_id,
                "alias": alias,
                "message": f"Automation '{alias}' erfolgreich erstellt!",
            }
        else:
            return {"error": f"HA API error ({resp.status_code}): {resp.text[:200]}"}
    except Exception as exc:
        return {"error": f"Failed to create automation: {exc}"}


def _execute_list_automations() -> dict:
    """List automations created by PilotSuite."""
    try:
        from flask import current_app
        services = current_app.config.get("COPILOT_SERVICES", {})
        creator = services.get("automation_creator")
        if creator:
            items = creator.list_created()
            return {"automations": items, "count": len(items)}
    except Exception:
        pass
    return {"automations": [], "count": 0, "message": "AutomationCreator not available"}


def _execute_web_search(args: dict) -> dict:
    """Search the web via WebSearchService."""
    try:
        from flask import current_app
        services = current_app.config.get("COPILOT_SERVICES", {})
        ws = services.get("web_search_service")
        if ws:
            query = args.get("query", "")
            max_results = min(int(args.get("max_results", 5)), 10)
            return ws.search(query, max_results=max_results)
    except Exception as exc:
        logger.warning("Web search failed: %s", exc)
    return {"error": "WebSearchService not available", "results": []}


def _execute_get_news(args: dict) -> dict:
    """Get current news headlines."""
    try:
        from flask import current_app
        services = current_app.config.get("COPILOT_SERVICES", {})
        ws = services.get("web_search_service")
        if ws:
            max_items = min(int(args.get("max_items", 10)), 20)
            return ws.get_news(max_items=max_items)
    except Exception as exc:
        logger.warning("News fetch failed: %s", exc)
    return {"error": "WebSearchService not available", "items": []}


def _execute_get_warnings() -> dict:
    """Get regional warnings (NINA + DWD)."""
    try:
        from flask import current_app
        services = current_app.config.get("COPILOT_SERVICES", {})
        ws = services.get("web_search_service")
        if ws:
            return ws.get_regional_warnings()
    except Exception as exc:
        logger.warning("Warning fetch failed: %s", exc)
    return {"error": "WebSearchService not available", "warnings": []}


def _execute_play_zone(args: dict) -> dict:
    """Control media playback in a habitus zone."""
    try:
        from flask import current_app
        services = current_app.config.get("COPILOT_SERVICES", {})
        mgr = services.get("media_zone_manager")
        if not mgr:
            return {"error": "MediaZoneManager not available"}

        zone_id = args.get("zone_id", "")
        action = args.get("action", "play")

        if action == "play":
            return mgr.play_zone(zone_id)
        elif action == "pause":
            return mgr.pause_zone(zone_id)
        elif action == "volume":
            vol = float(args.get("volume", 0.5))
            return mgr.set_zone_volume(zone_id, vol)
        elif action == "play_media":
            return mgr.play_media_in_zone(
                zone_id,
                args.get("media_content_id", ""),
                args.get("media_content_type", "music"),
            )
        else:
            return {"error": f"Unknown action: {action}"}
    except Exception as exc:
        logger.warning("Zone media control failed: %s", exc)
        return {"error": str(exc)}


def _execute_musikwolke(args: dict) -> dict:
    """Control Musikwolke (smart audio follow) sessions."""
    try:
        from flask import current_app
        services = current_app.config.get("COPILOT_SERVICES", {})
        mgr = services.get("media_zone_manager")
        if not mgr:
            return {"error": "MediaZoneManager not available"}

        action = args.get("action", "status")

        if action == "start":
            person_id = args.get("person_id", "")
            source_zone = args.get("source_zone", "")
            if not person_id or not source_zone:
                return {"error": "person_id and source_zone are required for start"}
            return mgr.start_musikwolke(person_id, source_zone)
        elif action == "stop":
            session_id = args.get("session_id", "")
            if not session_id:
                return {"error": "session_id is required for stop"}
            return mgr.stop_musikwolke(session_id)
        elif action == "status":
            sessions = mgr.get_musikwolke_sessions()
            return {"ok": True, "sessions": sessions, "count": len(sessions)}
        else:
            return {"error": f"Unknown action: {action}"}
    except Exception as exc:
        logger.warning("Musikwolke control failed: %s", exc)
        return {"error": str(exc)}


def _execute_waste_status() -> dict:
    """Get waste collection status."""
    try:
        from flask import current_app
        services = current_app.config.get("COPILOT_SERVICES", {})
        ws = services.get("waste_service")
        if ws:
            return ws.get_status()
    except Exception as exc:
        logger.warning("Waste status failed: %s", exc)
    return {"error": "WasteCollectionService not available", "collections": []}


def _execute_birthday_status() -> dict:
    """Get birthday status."""
    try:
        from flask import current_app
        services = current_app.config.get("COPILOT_SERVICES", {})
        bs = services.get("birthday_service")
        if bs:
            return bs.get_status()
    except Exception as exc:
        logger.warning("Birthday status failed: %s", exc)
    return {"error": "BirthdayService not available", "today": [], "upcoming": []}


def process_with_tool_execution(user_message: str) -> str:
    """Process a message with server-side tool execution.

    Used by Telegram bot and direct chat.  Handles the full tool-calling loop:
    LLM -> tool_calls -> execute via HA REST API -> feed results -> repeat.
    """
    messages = [{"role": "user", "content": user_message}]
    tools = _get_mcp_tools().get("functions", []) or None

    for _ in range(MAX_TOOL_ROUNDS):
        response = _process_conversation(messages, tools=tools)
        choice = response.get("choices", [{}])[0]
        msg = choice.get("message", {})

        if choice.get("finish_reason") != "tool_calls" or not msg.get("tool_calls"):
            return msg.get("content", "")

        # Append assistant message (with tool_calls) to conversation
        messages.append(msg)

        # Execute each tool and append results
        for tc in msg["tool_calls"]:
            fn = tc.get("function", {})
            tool_name = fn.get("name", "")
            try:
                tool_args = json.loads(fn.get("arguments", "{}"))
            except (json.JSONDecodeError, TypeError):
                tool_args = {}

            result = _execute_ha_tool(tool_name, tool_args)
            messages.append({
                "role": "tool",
                "content": json.dumps(result, default=str),
                "tool_call_id": tc.get("id", ""),
            })

    return msg.get("content", "") or "Maximale Tool-Runden erreicht."


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
