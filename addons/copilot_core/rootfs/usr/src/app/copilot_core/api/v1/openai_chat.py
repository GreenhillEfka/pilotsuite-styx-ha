"""OpenAI-compatible Chat Completions API for OpenClaw Assistant.

Provides /api/v1/openai/chat/completions endpoint
compatible with OpenAI API format for use with Extended OpenAI Conversation HACS.
"""
from __future__ import annotations

import logging
from flask import Blueprint, request, jsonify

from copilot_core.storage.events import EventStore
from copilot_core.mood.scoring import MoodScorer
from copilot_core.neurons.manager import NeuronManager, get_neuron_manager

bp = Blueprint("openai_chat", __name__, url_prefix="/api/v1/openai")

_logger = logging.getLogger(__name__)


def _event_store() -> EventStore | None:
    """Get event store singleton."""
    try:
        from copilot_core.api.v1.events import _store as events_store_factory
        return events_store_factory()
    except Exception:
        return None


def _mood_scorer() -> MoodScorer:
    """Get mood scorer singleton."""
    try:
        from copilot_core.mood.scoring import MoodScorer
        cfg = None
        window_seconds = 3600
        return MoodScorer(window_seconds=window_seconds)
    except Exception as e:
        _logger.error("Failed to create mood scorer: %s", e)
        return MoodScorer(window_seconds=3600)


def _neuron_manager() -> NeuronManager:
    """Get neuron manager singleton."""
    try:
        return get_neuron_manager()
    except Exception:
        return NeuronManager()


@bp.post("/chat/completions")
def chat_completions():
    """OpenAI-compatible chat completions endpoint.
    
    Accepts OpenAI-style request:
    {
        "model": "gpt-5.3-codex",
        "messages": [
            {"role": "user", "content": "Wie warm ist es im Wohnzimmer?"},
            {"role": "assistant", "content": "Im Wohnzimmer sind aktuell 22°C..."}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    Returns OpenAI-style response:
    {
        "id": "chatcmpl-xxx",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gpt-5.3-codex",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": "..."},
            "finish_reason": "stop"
        }]
    }
    
    Features:
    - Context-aware responses using HA states
    - Habitus pattern integration
    - Mood-based contextual awareness
    """
    try:
        payload = request.get_json(silent=True) or {}
        messages = payload.get("messages", [])
        model = payload.get("model", "gpt-5.3-codex")
        
        if not messages:
            return jsonify({
                "error": {"message": "messages array is required", "type": "invalid_request_error"}
            }), 400
        
        # Get recent context from HA
        context = _get_ha_context()
        
        # Get current mood
        mood_scorer = _mood_scorer()
        mood = mood_scorer.score_from_events(context.get("recent_events", []))
        
        # Build conversation context with HA data
        conversation_context = _build_conversation_context(messages, context, mood)
        
        # Generate response (simulated - would call actual LLM)
        response = _generate_response(messages, conversation_context, model)
        
        return jsonify({
            "id": "chatcmpl-" + str(hash(tuple(str(m) for m in messages)))[:28],
            "object": "chat.completion",
            "created": int(payload.get("created", 0)) or 1771344000,
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response
                },
                "finish_reason": "stop"
            }]
        })
        
    except Exception as e:
        _logger.exception("Chat completions failed")
        return jsonify({
            "error": {"message": str(e), "type": "server_error"}
        }), 500


def _get_ha_context() -> dict:
    """Get current HA context (states, recent events, mood)."""
    try:
        store = _event_store()
        recent_events = store.list(limit=100) if store else []
        
        return {
            "recent_events": recent_events,
            "states": [],  # Would fetch from hass.states
            "time": {"hour": 17, "day_of_week": "Tuesday"}
        }
    except Exception:
        return {"recent_events": [], "states": [], "time": {}}


def _build_conversation_context(
    messages: list,
    context: dict,
    mood: dict
) -> dict:
    """Build conversation context with HA data."""
    return {
        "ha_states": context.get("states", []),
        "recent_events": context.get("recent_events", []),
        "mood": mood,
        "time_context": context.get("time", {}),
        "user_context": {
            "current_users": [],  # From presence neurons
            "active_zones": []  # From Habitus zones
        }
    }


def _generate_response(
    messages: list,
    context: dict,
    model: str
) -> str:
    """Generate response based on messages and HA context."""
    last_message = messages[-1].get("content", "") if messages else ""
    
    # Simple context-aware response generation
    # In production, this would call the actual LLM
    
    response_parts = [
        "Ich bin bereit, dir zu helfen!",
        f"Aktueller Kontext: {len(context.get('ha_states', []))} Entitäten, {len(context.get('recent_events', []))} Events"
    ]
    
    if context.get("mood", {}).get("mood"):
        response_parts.append(f"Meine Stimmung: {context['mood']['mood'].get('mood', 'unbekannt')}")
    
    if "temperatur" in last_message.lower() or "warm" in last_message.lower():
        response_parts.append("Ich habe keine direkte Temperaturangabe, aber ich kann Sensoren abfragen.")
    
    if "licht" in last_message.lower() or "beleuchtung" in last_message.lower():
        response_parts.append("Ich kann Lichtsteuerung empfehlen basierend auf deinem Habitus-Muster.")
    
    return " ".join(response_parts) + " Wie kann ich dir weiterhelfen?"


@bp.get("/models")
def list_models():
    """List available OpenAI-compatible models."""
    return jsonify({
        "object": "list",
        "data": [
            {
                "id": "gpt-5.3-codex",
                "object": "model",
                "created": 1700000000,
                "owned_by": "pilotsuite"
            },
            {
                "id": "gpt-5.2-codex",
                "object": "model",
                "created": 1700000000,
                "owned_by": "pilotsuite"
            }
        ]
    })
