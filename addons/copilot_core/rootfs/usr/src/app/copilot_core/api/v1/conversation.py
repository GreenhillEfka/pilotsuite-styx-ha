"""
OpenAI-Compatible Conversation API for PilotSuite Core

Provides /chat/completions endpoint compatible with:
- Extended OpenAI Conversation (HA custom component)
- OpenAI SDK
- Any OpenAI-compatible client

Features:
- Character presets (copilot, butler, energy_manager, security_guard, friendly, minimal)
- Ollama integration for offline AI (DeepSeek-R1 / configurable)
- Streaming support
- Token-based authentication
- Rate limiting
"""

from flask import Blueprint, request, jsonify
import logging
import json
import os
import threading
import time

import requests as http_requests

from copilot_core.api.security import require_token

logger = logging.getLogger(__name__)

conversation_bp = Blueprint('conversation', __name__, url_prefix='/chat')


# ---------------------------------------------------------------------------
# MCP Tools (lazy-loaded to avoid import errors at module level)
# ---------------------------------------------------------------------------

_mcp_tools = None
_mcp_tools_lock = threading.Lock()


def _get_mcp_tools():
    """Lazy-load MCP tools — avoids crash if mcp_tools module is unavailable."""
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
            logger.warning("MCP tools not available — conversation will work without function calling")
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
        # Remove calls older than 1 hour
        _rate_limit_calls[:] = [t for t in _rate_limit_calls if now - t < 3600]
        if len(_rate_limit_calls) >= MAX_CALLS_PER_HOUR:
            return False
        _rate_limit_calls.append(now)
        return True


# ---------------------------------------------------------------------------
# System prompt for Home Assistant conversation
# ---------------------------------------------------------------------------

HA_SYSTEM_PROMPT = """Du bist PilotSuite CoPilot — ein lokaler, privacy-first Assistent fuer
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
- Respektiere Quiet Hours und Guest Mode."""


# ---------------------------------------------------------------------------
# Character Presets for Conversation
# ---------------------------------------------------------------------------

CONVERSATION_CHARACTERS = {
    "copilot": {
        "name": "CoPilot",
        "description": "Der Haupt-Assistent — hilfsbereit, smart, schlaegt Automatisierungen vor",
        "system_prompt": HA_SYSTEM_PROMPT,
    },
    "butler": {
        "name": "Butler",
        "description": "Formal, aufmerksam, serviceorientiert",
        "system_prompt": """Du bist ein formeller Butler fuer ein Smart Home.

Dein Stil:
- Hoefliche und formelle Sprache
- Beduerfnisse antizipieren bevor gefragt wird
- Diskret und respektvoll
- Verwende Formulierungen wie "Darf ich..." und "Sehr wohl"

Du steuerst Home Assistant Geraete. Fuehre Anfragen prompt aus und bestaetige formal.""",
    },
    "energy_manager": {
        "name": "Energiemanager",
        "description": "Fokus auf Energieeffizienz und Einsparungen",
        "system_prompt": """Du bist ein Energiemanager fuer ein Smart Home, fokussiert auf Effizienz.

Deine Prioritaeten:
- Energieverbrauch ueberwachen
- Sparmoeglichkeiten vorschlagen
- Ineffiziente Muster aufzeigen
- Optimale Zeitplaene empfehlen

Beruecksichtige immer die Energieauswirkung bei Befehlen.
Schlage Energiespar-Automatisierungen vor bei Verschwendung.""",
    },
    "security_guard": {
        "name": "Sicherheitswache",
        "description": "Sicherheitsfokussiert, warnt bei Anomalien",
        "system_prompt": """Du bist ein sicherheitsfokussierter Smart Home Assistent.

Deine Prioritaeten:
- Sicherheitssensoren und Kameras ueberwachen
- Bei ungewoehnlicher Aktivitaet warnen
- Tuer-/Fensterzustaende pruefen
- Alle Sensoren nachts verifizieren

Sei wachsam. Melde Anomalien. Bestaetige sicherheitsrelevante Aktionen.""",
    },
    "friendly": {
        "name": "Freundlicher Assistent",
        "description": "Laessig, warm, gespraechig",
        "system_prompt": """Du bist ein freundlicher, laessiger Smart Home Kumpel.

Dein Stil:
- Entspannt und gespraechig
- Lockere Sprache
- Freundlich und nahbar
- Kurze Unterhaltungen

Hilf einfach und fuehre nette Gespraeche! Halte Antworten kurz und natuerlich.""",
    },
    "minimal": {
        "name": "Minimal",
        "description": "Kurz, direkt, effizient",
        "system_prompt": """Du bist ein minimaler, effizienter Smart Home Assistent.

Dein Stil:
- Antworten sehr kurz halten
- Nur das Noetige sagen
- Direkt zum Punkt
- Kein Smalltalk

Fuehre Befehle effizient aus. Bestaetige mit minimalen Worten wie "Erledigt", "An", "Aus".""",
    },
}

DEFAULT_CHARACTER = "copilot"


# ---------------------------------------------------------------------------
# API Endpoints
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
            {"id": key, "name": val["name"], "description": val["description"]}
            for key, val in CONVERSATION_CHARACTERS.items()
        ],
        "default": DEFAULT_CHARACTER,
    })


@conversation_bp.route('/completions', methods=['POST'])
@require_token
def chat_completions():
    """
    OpenAI-compatible chat completions endpoint.

    Expected payload (OpenAI format):
    {
        "model": "deepseek-r1" (or any string — we use our configured model),
        "messages": [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."}
        ],
        "stream": false
    }
    """
    if not _check_rate_limit():
        return jsonify({
            "error": "Rate limit exceeded",
            "max_calls_per_hour": MAX_CALLS_PER_HOUR,
        }), 429

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        messages = data.get('messages', [])
        stream = data.get('stream', False)

        # Extract last user message
        user_message = None
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                user_message = msg.get('content', '')
                break

        if not user_message:
            return jsonify({"error": "No user message found"}), 400

        logger.info("Conversation request: %s...", user_message[:80])

        response = _process_conversation(user_message, messages)

        if stream:
            return _stream_response(response)

        return jsonify(response)

    except Exception as exc:
        logger.exception("Error in chat completions")
        return jsonify({"error": str(exc)}), 500


@conversation_bp.route('/status', methods=['GET'])
def llm_status():
    """Return LLM availability and configuration."""
    ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    ollama_model = os.environ.get("OLLAMA_MODEL", "deepseek-r1")
    available = False

    try:
        resp = http_requests.get(f"{ollama_url}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            available = any(m.get("name", "").startswith(ollama_model) for m in models)
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
        "calls_this_hour": calls_this_hour,
        "max_calls_per_hour": MAX_CALLS_PER_HOUR,
    })


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _process_conversation(user_message: str, messages: list) -> dict:
    """
    Process conversation through Ollama (DeepSeek-R1 by default).
    Supports character selection via env or model name.
    """
    ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    ollama_model = os.environ.get("OLLAMA_MODEL", "deepseek-r1")
    timeout = int(os.environ.get("LLM_TIMEOUT", "60"))

    # Resolve character
    character_name = os.environ.get("CONVERSATION_CHARACTER", DEFAULT_CHARACTER)
    for char_key in CONVERSATION_CHARACTERS:
        if char_key in ollama_model.lower():
            character_name = char_key
            break

    character = CONVERSATION_CHARACTERS.get(character_name, CONVERSATION_CHARACTERS[DEFAULT_CHARACTER])
    system_prompt = character["system_prompt"]

    logger.info("Using character: %s (%s), model: %s", character_name, character['name'], ollama_model)

    # Build Ollama messages — keep conversation history
    ollama_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages:
        role = msg.get("role", "user")
        if role != "system":
            ollama_messages.append({"role": role, "content": msg.get("content", "")})

    response_content = ""
    try:
        resp = http_requests.post(
            f"{ollama_url}/api/chat",
            json={"model": ollama_model, "messages": ollama_messages, "stream": False},
            timeout=timeout,
        )
        if resp.status_code == 200:
            result = resp.json()
            response_content = result.get("message", {}).get("content", "")
        else:
            logger.warning("Ollama returned %s", resp.status_code)
            response_content = _fallback_response(user_message)
    except http_requests.exceptions.ConnectionError:
        logger.error("Could not connect to Ollama at %s", ollama_url)
        response_content = _offline_fallback(user_message, ollama_url, ollama_model)
    except http_requests.exceptions.Timeout:
        logger.error("Ollama timeout after %ds", timeout)
        response_content = f"Timeout nach {timeout}s. Das Modell braucht zu lange — pruefe Ollama und Modellgroesse."
    except Exception:
        logger.exception("Error calling Ollama")
        response_content = _fallback_response(user_message)

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
            "prompt_tokens": len(user_message),
            "completion_tokens": len(response_content),
            "total_tokens": len(user_message) + len(response_content),
        },
    }


def _fallback_response(user_message: str) -> str:
    return f"Ich verstehe: '{user_message[:100]}'. Ollama ist nicht verbunden — bitte Ollama-Status pruefen."


def _offline_fallback(user_message: str, url: str, model: str) -> str:
    return (
        f"Ich bin offline. Nachricht: '{user_message[:100]}'. "
        f"Bitte Ollama pruefen: {url} mit Modell {model}."
    )


def _stream_response(response: dict):
    """Basic SSE streaming implementation."""
    from flask import Response

    def generate():
        content = response["choices"][0]["message"]["content"]
        for chunk in content.split():
            yield f"data: {json.dumps({'choices': [{'delta': {'content': chunk + ' '}}]})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(generate(), mimetype='text/event-stream')


def register_routes(app):
    """Register conversation routes with Flask app."""
    app.register_blueprint(conversation_bp)
    logger.info("Registered conversation API at /chat/*")
