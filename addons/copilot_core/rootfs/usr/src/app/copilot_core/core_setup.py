"""
Core Setup - Service initialization and blueprint registration.

Extracted from main.py to follow modular architecture pattern.
"""

import logging
from flask import Flask

from copilot_core.api.v1 import log_fixer_tx
from copilot_core.api.v1 import events_ingest
from copilot_core.api.v1.events_ingest import set_post_ingest_callback
from copilot_core.brain_graph.api import brain_graph_bp, init_brain_graph_api
from copilot_core.brain_graph.service import BrainGraphService
from copilot_core.brain_graph.store import BrainGraphStore

# Alias for backwards compatibility
GraphStore = BrainGraphStore
from copilot_core.brain_graph.render import GraphRenderer
from copilot_core.ingest.event_processor import EventProcessor
from copilot_core.dev_surface.api import dev_surface_bp, init_dev_surface_api
from copilot_core.candidates.api import candidates_bp, init_candidates_api
from copilot_core.candidates.store import CandidateStore
from copilot_core.habitus.api import habitus_bp, init_habitus_api
from copilot_core.habitus.service import HabitusService
from copilot_core.mood.api import mood_bp, init_mood_api
from copilot_core.mood.service import MoodService
from copilot_core.system_health.api import system_health_bp
from copilot_core.system_health.service import SystemHealthService
from copilot_core.unifi.api import unifi_bp, set_unifi_service
from copilot_core.unifi.service import UniFiService
from copilot_core.energy.api import energy_bp, init_energy_api
from copilot_core.energy.service import EnergyService
# Tag System v0.2 (Decision Matrix 2026-02-14)
from copilot_core.tags import TagRegistry, create_tag_service
from copilot_core.tags.api import init_tags_api as setup_tag_api
from copilot_core.webhook_pusher import WebhookPusher
from copilot_core.household import HouseholdProfile
from copilot_core.neurons.manager import NeuronManager

_LOGGER = logging.getLogger(__name__)


def _safe_int(value, default: int, minimum: int = 1) -> int:
    """Parse an int config value with bounds checking."""
    try:
        return max(minimum, int(value))
    except (TypeError, ValueError):
        return default


def _safe_float(value, default: float, minimum: float = 0.0) -> float:
    """Parse a float config value with bounds checking."""
    try:
        return max(minimum, float(value))
    except (TypeError, ValueError):
        return default


def init_services(hass=None, config: dict = None):
    """
    Initialize all core services and return them as a dict for testing/dependency injection.

    Each service block is wrapped in try/except so a single failure does not
    prevent the remaining services from starting.
    """
    services: dict = {
        "system_health_service": None,
        "unifi_service": None,
        "energy_service": None,
        "brain_graph_service": None,
        "graph_renderer": None,
        "candidate_store": None,
        "habitus_service": None,
        "mood_service": None,
        "event_processor": None,
        "tag_registry": None,
        "webhook_pusher": None,
        "household_profile": None,
        "neuron_manager": None,
    }

    # Initialize system health service (requires hass)
    try:
        if hass:
            services["system_health_service"] = SystemHealthService(hass)
    except Exception:
        _LOGGER.exception("Failed to init SystemHealthService")

    # Initialize UniFi service (requires hass)
    try:
        if hass:
            services["unifi_service"] = UniFiService(hass)
    except Exception:
        _LOGGER.exception("Failed to init UniFiService")

    # Initialize energy service (requires hass)
    try:
        if hass:
            services["energy_service"] = EnergyService(hass)
    except Exception:
        _LOGGER.exception("Failed to init EnergyService")

    # Parse Brain Graph configuration with validation
    try:
        bg_config = config.get("brain_graph", {}) if config else {}
        brain_graph_service = BrainGraphService(
            store=GraphStore(
                max_nodes=_safe_int(bg_config.get("max_nodes", 500), 500, 1),
                max_edges=_safe_int(bg_config.get("max_edges", 1500), 1500, 1),
                node_min_score=_safe_float(bg_config.get("node_min_score", 0.1), 0.1),
                edge_min_weight=_safe_float(bg_config.get("edge_min_weight", 0.1), 0.1)
            ),
            node_half_life_hours=_safe_float(bg_config.get("node_half_life_hours", 24.0), 24.0, 0.1),
            edge_half_life_hours=_safe_float(bg_config.get("edge_half_life_hours", 12.0), 12.0, 0.1)
        )
        services["brain_graph_service"] = brain_graph_service
        services["graph_renderer"] = GraphRenderer()
        init_brain_graph_api(brain_graph_service, services["graph_renderer"])
    except Exception:
        _LOGGER.exception("Failed to init BrainGraphService")

    # Initialize dev surface
    try:
        if services["brain_graph_service"]:
            init_dev_surface_api(services["brain_graph_service"])
    except Exception:
        _LOGGER.exception("Failed to init DevSurface")

    # Initialize candidates API and store
    try:
        candidate_store = CandidateStore()
        services["candidate_store"] = candidate_store
        init_candidates_api(candidate_store)
    except Exception:
        _LOGGER.exception("Failed to init CandidateStore")

    # Initialize habitus service and API
    try:
        if services["brain_graph_service"] and services["candidate_store"]:
            habitus_service = HabitusService(services["brain_graph_service"], services["candidate_store"])
            services["habitus_service"] = habitus_service
            init_habitus_api(habitus_service)
    except Exception:
        _LOGGER.exception("Failed to init HabitusService")

    # Initialize mood service and API
    try:
        mood_service = MoodService()
        services["mood_service"] = mood_service
        init_mood_api(mood_service)
    except Exception:
        _LOGGER.exception("Failed to init MoodService")

    # Initialize event processor: EventStore → BrainGraph pipeline
    try:
        if services["brain_graph_service"]:
            event_processor = EventProcessor(brain_graph_service=services["brain_graph_service"])
            services["event_processor"] = event_processor
            set_post_ingest_callback(event_processor.process_events)
    except Exception:
        _LOGGER.exception("Failed to init EventProcessor")

    # Initialize Tag System v0.2 (Decision Matrix 2026-02-14)
    try:
        services["tag_registry"] = TagRegistry()
    except Exception:
        _LOGGER.exception("Failed to init TagRegistry")

    # Initialize Webhook Pusher
    try:
        webhook_url = config.get("webhook_url", "") if config else ""
        webhook_token = config.get("webhook_token", "") if config else ""
        services["webhook_pusher"] = WebhookPusher(webhook_url, webhook_token)
    except Exception:
        _LOGGER.exception("Failed to init WebhookPusher")

    # Initialize Household Profile
    try:
        household_config = config.get("household", {}) if config else {}
        services["household_profile"] = HouseholdProfile.from_config(household_config)
    except Exception:
        _LOGGER.exception("Failed to init HouseholdProfile")

    # NeuronManager: Household-Profil setzen, configure_from_ha, und Webhook-Callbacks registrieren
    try:
        neuron_config = config.get("neurons", {}) if config else {}
        neuron_manager = NeuronManager()
        if services["household_profile"]:
            neuron_manager.set_household(services["household_profile"])
        neuron_manager.configure_from_ha({}, neuron_config)
        webhook_pusher = services.get("webhook_pusher")
        if webhook_pusher and webhook_pusher.enabled:
            neuron_manager.on_mood_change(
                lambda mood, conf: webhook_pusher.push_mood_changed(mood, conf)
            )
            neuron_manager.on_suggestion(
                lambda suggestion: webhook_pusher.push_suggestion(suggestion)
            )
        services["neuron_manager"] = neuron_manager
    except Exception:
        _LOGGER.exception("Failed to init NeuronManager")

    # Set conversation env vars from config (used by conversation.py)
    try:
        conv_config = config.get("conversation", {}) if config else {}
        if conv_config.get("ollama_url"):
            import os
            os.environ.setdefault("OLLAMA_URL", conv_config["ollama_url"])
        if conv_config.get("ollama_model"):
            import os
            os.environ.setdefault("OLLAMA_MODEL", conv_config["ollama_model"])
        if conv_config.get("character"):
            import os
            os.environ.setdefault("CONVERSATION_CHARACTER", conv_config["character"])
        if conv_config.get("enabled"):
            import os
            os.environ.setdefault("CONVERSATION_ENABLED", "true")
    except Exception:
        _LOGGER.exception("Failed to set conversation env vars")

    return services


def register_blueprints(app: Flask, services: dict = None) -> None:
    """
    Register all API blueprints with the Flask app.
    
    Args:
        app: Flask application instance
        services: Optional services dict from init_services() for global access
    """
    # Import performance blueprint
    from copilot_core.api.performance import performance_bp
    
    app.register_blueprint(log_fixer_tx.bp)
    app.register_blueprint(events_ingest.bp)
    app.register_blueprint(brain_graph_bp)
    app.register_blueprint(dev_surface_bp)
    app.register_blueprint(candidates_bp)
    app.register_blueprint(habitus_bp)
    app.register_blueprint(mood_bp)
    app.register_blueprint(system_health_bp)
    app.register_blueprint(unifi_bp)
    app.register_blueprint(energy_bp)
    app.register_blueprint(performance_bp)  # Performance monitoring

    # Register Conversation/LLM API (Ollama / lfm2.5-thinking)
    try:
        from copilot_core.api.v1.conversation import conversation_bp, openai_compat_bp
        app.register_blueprint(conversation_bp)
        app.register_blueprint(openai_compat_bp)
        _LOGGER.info("Registered conversation API (/chat/* and /v1/*)")
    except Exception:
        _LOGGER.exception("Failed to register conversation blueprint")

    # Register Tag System v0.2 blueprint (Decision Matrix 2026-02-14)
    # init_tags_api sets the global registry; the bp is already defined in tags/api.py
    if services and services.get("tag_registry"):
        setup_tag_api(services["tag_registry"])
    from copilot_core.tags.api import bp as tags_bp
    app.register_blueprint(tags_bp)
    
    # Store services in app config for conversation context injection
    if services:
        app.config["COPILOT_SERVICES"] = services

    # Set global service instances for API access
    if services:
        from copilot_core import set_system_health_service
        if services.get("system_health_service"):
            set_system_health_service(services["system_health_service"])
        
        # Set SQL connection pool
        from copilot_core.performance import sql_pool
        if sql_pool:
            sql_pool.max_connections = 5  # Configure pool size
        
        # Set UniFi service for API access
        from copilot_core.unifi import set_unifi_service as set_unifi
        if services.get("unifi_service"):
            set_unifi(services["unifi_service"])
        
        # Set Energy service for API access
        from copilot_core.energy.api import init_energy_api
        if services.get("energy_service"):
            init_energy_api(services["energy_service"])
