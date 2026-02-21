"""Styx Agent Auto-Config & Health Check (v5.21.0).

Provides endpoints to verify agent connectivity, report status,
and configure agent personality for the HA conversation integration.
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime

from flask import Blueprint, jsonify, request

from copilot_core.api.security import require_token

logger = logging.getLogger(__name__)

agent_config_bp = Blueprint("agent_config", __name__, url_prefix="/api/v1/agent")

# ── Data classes ─────────────────────────────────────────────────────────


@dataclass
class AgentStatus:
    """Styx agent health and status."""

    agent_name: str
    agent_version: str
    status: str  # "ready", "degraded", "offline"
    uptime_seconds: float
    conversation_ready: bool
    llm_available: bool
    llm_model: str
    llm_backend: str  # "ollama", "cloud", "none"
    supported_languages: list[str]
    character: str
    features: list[str]
    last_health_check: str


@dataclass
class AgentCapabilities:
    """What the agent can do."""

    conversation: bool
    tool_calling: bool
    web_search: bool
    automation_creation: bool
    energy_management: bool
    mood_tracking: bool
    brain_graph: bool
    regional_context: bool
    proactive_alerts: bool
    multilingual: bool
    characters: list[str]


@dataclass
class AgentGreeting:
    """Greeting message for new installations."""

    language: str
    greeting: str
    introduction: str
    capabilities_summary: str
    setup_hints: list[str]


# ── Module state ─────────────────────────────────────────────────────────

_start_time: float = time.time()
_config: dict = {}
_llm_provider = None
_conversation_module = None


def init_agent_config(
    config: dict | None = None,
    llm_provider=None,
    conversation_module=None,
) -> None:
    """Initialize agent config module."""
    global _config, _llm_provider, _conversation_module, _start_time
    _config = config or {}
    _llm_provider = llm_provider
    _conversation_module = conversation_module
    _start_time = time.time()
    logger.info("Agent config module initialized")


def _get_agent_version() -> str:
    """Get current agent version from config."""
    return _config.get("version", "5.21.0")


def _check_llm_available() -> tuple[bool, str, str]:
    """Check if LLM backend is available."""
    conv_config = _config.get("conversation", {})
    prefer_local = conv_config.get("prefer_local", True)

    if prefer_local:
        ollama_url = conv_config.get("ollama_url", "http://localhost:11434")
        model = conv_config.get("ollama_model", "qwen3:4b")
        # We don't do a live check here — just report the configured state
        return True, model, "ollama"

    cloud_url = conv_config.get("cloud_api_url", "")
    cloud_model = conv_config.get("cloud_model", "")
    if cloud_url and cloud_model:
        return True, cloud_model, "cloud"

    return False, "", "none"


def _get_features() -> list[str]:
    """List enabled features."""
    features = ["conversation"]

    conv = _config.get("conversation", {})
    if conv.get("enabled", True):
        features.append("chat_completions")

    if _config.get("openai_api", {}).get("enabled", True):
        features.append("openai_compatible_api")

    if _config.get("brain_graph", {}).get("max_nodes", 0) > 0:
        features.append("brain_graph")

    if _config.get("knowledge_graph", {}).get("enabled", False):
        features.append("knowledge_graph")

    if _config.get("user_preferences", {}).get("enabled", False):
        features.append("user_preferences")

    if _config.get("telegram", {}).get("enabled", False):
        features.append("telegram")

    if _config.get("web_search", {}).get("ags_code"):
        features.append("regional_news")

    features.append("regional_context")
    features.append("energy_forecast")
    features.append("proactive_alerts")

    return features


def _get_character() -> str:
    """Get active character preset."""
    return _config.get("conversation", {}).get("character", "copilot")


# ── Greeting templates ───────────────────────────────────────────────────

_GREETINGS = {
    "de": AgentGreeting(
        language="de",
        greeting="Hallo! Ich bin Styx, dein lokaler KI-Assistent von PilotSuite.",
        introduction=(
            "Ich laufe vollstaendig lokal auf deinem Home Assistant — "
            "keine Cloud, keine Daten die dein Zuhause verlassen. "
            "Ich kann dir bei der Steuerung deines Smart Homes helfen, "
            "Energieoptimierung durchfuehren, Automationen erstellen "
            "und vieles mehr."
        ),
        capabilities_summary=(
            "Meine Faehigkeiten: Gespraeche fuehren, Geraete steuern, "
            "Energieprognosen erstellen, Wetterwarnungen auswerten, "
            "Strompreise optimieren, Stimmung und Gewohnheiten lernen."
        ),
        setup_hints=[
            "Oeffne Einstellungen > Sprachassistenten und waehle PilotSuite als Gesprächsagent",
            "Nutze das PilotSuite Dashboard fuer Stimmung, Neuronen und Habitus",
            "Konfiguriere Habitus-Zonen unter Einstellungen > Integrationen > PilotSuite",
            "Alle Verarbeitung laeuft lokal — keine Cloud erforderlich",
        ],
    ),
    "en": AgentGreeting(
        language="en",
        greeting="Hello! I'm Styx, your local AI assistant from PilotSuite.",
        introduction=(
            "I run entirely locally on your Home Assistant — "
            "no cloud, no data leaving your home. "
            "I can help you control your smart home, "
            "optimize energy usage, create automations, "
            "and much more."
        ),
        capabilities_summary=(
            "My capabilities: conversations, device control, "
            "energy forecasts, weather warnings, electricity price optimization, "
            "mood tracking, and habit learning."
        ),
        setup_hints=[
            "Open Settings > Voice Assistants and select PilotSuite as conversation agent",
            "Use the PilotSuite dashboard for Mood, Neurons, and Habitus cards",
            "Configure Habitus zones via Settings > Integrations > PilotSuite",
            "All processing runs locally — no cloud required",
        ],
    ),
}


# ── API endpoints ────────────────────────────────────────────────────────


@agent_config_bp.route("/status", methods=["GET"])
@require_token
def get_agent_status():
    """Get Styx agent health status."""
    llm_available, llm_model, llm_backend = _check_llm_available()

    status = AgentStatus(
        agent_name=_config.get("conversation", {}).get("assistant_name", "Styx"),
        agent_version=_get_agent_version(),
        status="ready" if llm_available else "degraded",
        uptime_seconds=round(time.time() - _start_time, 1),
        conversation_ready=True,
        llm_available=llm_available,
        llm_model=llm_model,
        llm_backend=llm_backend,
        supported_languages=["de", "en"],
        character=_get_character(),
        features=_get_features(),
        last_health_check=datetime.now().isoformat(),
    )
    return jsonify({"ok": True, **asdict(status)})


@agent_config_bp.route("/capabilities", methods=["GET"])
@require_token
def get_agent_capabilities():
    """Get what the agent can do."""
    features = _get_features()

    caps = AgentCapabilities(
        conversation=True,
        tool_calling="chat_completions" in features,
        web_search="regional_news" in features,
        automation_creation=True,
        energy_management="energy_forecast" in features,
        mood_tracking="brain_graph" in features,
        brain_graph="brain_graph" in features,
        regional_context="regional_context" in features,
        proactive_alerts="proactive_alerts" in features,
        multilingual=True,
        characters=["copilot", "butler", "energy_manager", "security_guard", "friendly", "minimal"],
    )
    return jsonify({"ok": True, **asdict(caps)})


@agent_config_bp.route("/greeting", methods=["GET"])
@require_token
def get_greeting():
    """Get installation greeting message."""
    lang = request.args.get("lang", "de")
    greeting = _GREETINGS.get(lang, _GREETINGS["en"])
    return jsonify({"ok": True, **asdict(greeting)})


@agent_config_bp.route("/ping", methods=["GET"])
@require_token
def agent_ping():
    """Simple ping to verify agent is alive — for bidirectional check."""
    return jsonify({
        "ok": True,
        "pong": True,
        "agent": _config.get("conversation", {}).get("assistant_name", "Styx"),
        "timestamp": datetime.now().isoformat(),
    })


@agent_config_bp.route("/verify", methods=["POST"])
@require_token
def verify_bidirectional():
    """Verify bidirectional communication (HA sends, Core responds with echo + status).

    JSON body: {"message": "hello", "source": "ha_integration"}
    """
    body = request.get_json(silent=True) or {}
    message = body.get("message", "")
    source = body.get("source", "unknown")

    llm_available, llm_model, llm_backend = _check_llm_available()

    return jsonify({
        "ok": True,
        "echo": message,
        "source_received": source,
        "agent_name": _config.get("conversation", {}).get("assistant_name", "Styx"),
        "agent_ready": True,
        "llm_available": llm_available,
        "llm_model": llm_model,
        "features": _get_features(),
        "timestamp": datetime.now().isoformat(),
    })
