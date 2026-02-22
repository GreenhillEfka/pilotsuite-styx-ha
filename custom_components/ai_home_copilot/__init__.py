from __future__ import annotations

from importlib import import_module
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .blueprints import async_install_blueprints
from .const import DOMAIN
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
from .core.runtime import CopilotRuntime
from .services_setup import async_register_all_services

_LOGGER = logging.getLogger(__name__)

_MODULE_IMPORTS = {
    "legacy": (".core.modules.legacy", "LegacyModule"),
    "performance_scaling": (".core.modules.performance_scaling", "PerformanceScalingModule"),
    "events_forwarder": (".core.modules.events_forwarder", "EventsForwarderModule"),
    "history_backfill": (".core.modules.history_backfill", "HistoryBackfillModule"),
    "dev_surface": (".core.modules.dev_surface", "DevSurfaceModule"),
    "habitus_miner": (".core.modules.habitus_miner", "HabitusMinerModule"),
    "ops_runbook": (".core.modules.ops_runbook", "OpsRunbookModule"),
    "unifi_module": (".core.modules.unifi_module", "UniFiModule"),
    "brain_graph_sync": (".core.modules.brain_graph_sync", "BrainGraphSyncModule"),
    "candidate_poller": (".core.modules.candidate_poller", "CandidatePollerModule"),
    "media_zones": (".core.modules.media_context_module", "MediaContextModule"),
    "mood": (".core.modules.mood_module", "MoodModule"),
    "mood_context": (".core.modules.mood_context_module", "MoodContextModule"),
    "energy_context": (".core.modules.energy_context_module", "EnergyContextModule"),
    "network": (".core.modules.unifi_context_module", "UnifiContextModule"),
    "weather_context": (".core.modules.weather_context_module", "WeatherContextModule"),
    "knowledge_graph_sync": (".core.modules.knowledge_graph_sync", "KnowledgeGraphSyncModule"),
    "ml_context": (".core.modules.ml_context_module", "MLContextModule"),
    "camera_context": (".core.modules.camera_context_module", "CameraContextModule"),
    "quick_search": (".core.modules.quick_search", "QuickSearchModule"),
    "voice_context": (".core.modules.voice_context", "VoiceContextModule"),
    "home_alerts": (".core.modules.home_alerts_module", "HomeAlertsModule"),
    "character_module": (".core.modules.character_module", "CharacterModule"),
    "waste_reminder": (".core.modules.waste_reminder_module", "WasteReminderModule"),
    "birthday_reminder": (".core.modules.birthday_reminder_module", "BirthdayReminderModule"),
    "entity_tags": (".core.modules.entity_tags_module", "EntityTagsModule"),
    "person_tracking": (".core.modules.person_tracking_module", "PersonTrackingModule"),
    "frigate_bridge": (".core.modules.frigate_bridge", "FrigateBridgeModule"),
    "scene_module": (".core.modules.scene_module", "SceneModule"),
    "homekit_bridge": (".core.modules.homekit_bridge", "HomeKitBridgeModule"),
    "calendar_module": (".core.modules.calendar_module", "CalendarModule"),
}

_MODULES = [
    "legacy",
    "performance_scaling",
    "events_forwarder",
    "history_backfill",
    "dev_surface",
    "habitus_miner",
    "ops_runbook",
    "unifi_module",
    "brain_graph_sync",
    "candidate_poller",
    "media_zones",
    "mood",
    "mood_context",
    "energy_context",
    "network",
    "weather_context",
    "knowledge_graph_sync",
    "ml_context",
    "camera_context",
    "quick_search",
    "voice_context",
    "home_alerts",
    "character_module",
    "waste_reminder",
    "birthday_reminder",
    "entity_tags",
    "person_tracking",
    "frigate_bridge",
    "scene_module",
    "homekit_bridge",
    "calendar_module",
]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    async_register_all_services(hass)
    
    # Register Quick Search services
    from .search_integration import async_register_services as register_search_services
    await register_search_services(hass)
    
    return True


def _get_runtime(hass: HomeAssistant) -> CopilotRuntime:
    runtime = CopilotRuntime.get(hass)

    for name, (module_path, class_name) in _MODULE_IMPORTS.items():
        if name not in runtime.registry.names():
            try:
                module = import_module(module_path, package=__package__)
                cls = getattr(module, class_name)
                runtime.registry.register(name, cls)
            except Exception:
                _LOGGER.exception(
                    "Failed to register module '%s' (%s:%s) — skipping",
                    name,
                    module_path,
                    class_name,
                )
    return runtime


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await async_install_blueprints(hass)
    runtime = _get_runtime(hass)
    await runtime.async_setup_entry(entry, modules=_MODULES)
    
    # Set up User Preference Module separately (not a CopilotModule)
    try:
        from .user_preference_module import UserPreferenceModule
        from .const import CONF_USER_PREFERENCE_ENABLED

        config = entry.options or entry.data
        if config.get(CONF_USER_PREFERENCE_ENABLED, False):
            user_pref_module = UserPreferenceModule(hass, entry)
            await user_pref_module.async_setup()

            if DOMAIN not in hass.data:
                hass.data[DOMAIN] = {}
            if entry.entry_id not in hass.data[DOMAIN]:
                hass.data[DOMAIN][entry.entry_id] = {}
            hass.data[DOMAIN][entry.entry_id]["user_preference_module"] = user_pref_module
    except Exception:
        _LOGGER.exception("Failed to set up UserPreferenceModule")
    
    # Set up Multi-User Preference Learning Module (v0.8.0)
    try:
        from .multi_user_preferences import MultiUserPreferenceModule, set_mupl_module
        from .const import CONF_MUPL_ENABLED, DEFAULT_MUPL_ENABLED

        config = entry.options or entry.data
        if config.get(CONF_MUPL_ENABLED, DEFAULT_MUPL_ENABLED):
            mupl_module = MultiUserPreferenceModule(hass, entry)
            await mupl_module.async_setup()
            set_mupl_module(hass, entry.entry_id, mupl_module)
            _LOGGER.info("Multi-User Preference Learning Module initialized")
    except Exception:
        _LOGGER.exception("Failed to set up MultiUserPreferenceModule")

    # Set up Zone Detector with Core addon forwarding (v3.1.0)
    try:
        from .zone_detector import ZoneDetector
        entry_store = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
        coord = entry_store.get("coordinator") if isinstance(entry_store, dict) else None
        api_client = getattr(coord, "api", None) if coord else None
        zone_detector = ZoneDetector(hass, entry, api_client=api_client)
        await zone_detector.async_setup()
        if isinstance(entry_store, dict):
            entry_store["zone_detector"] = zone_detector
        _LOGGER.info("ZoneDetector initialized (proactive zone-entry forwarding active)")
    except Exception:
        _LOGGER.exception("Failed to set up ZoneDetector")

    # Register PilotSuite conversation agent (v3.10.0)
    try:
        from .conversation import async_setup_conversation
        await async_setup_conversation(hass, entry)
    except Exception:
        _LOGGER.exception("Failed to set up conversation agent")

    # Auto-configure Styx as default conversation agent (v5.21.0)
    try:
        from .agent_auto_config import async_setup_agent_auto_config
        await async_setup_agent_auto_config(hass, entry)
    except Exception:
        _LOGGER.exception("Failed to set up agent auto-config")

    # Register Lovelace card resources from Core Add-on
    try:
        from .lovelace_resources import async_register_card_resources
        await async_register_card_resources(hass, entry)
    except Exception:
        _LOGGER.exception("Failed to register Lovelace card resources")

    # Auto-generate PilotSuite dashboard on first setup
    try:
        from .pilotsuite_dashboard import async_generate_pilotsuite_dashboard
        entry_store = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
        if isinstance(entry_store, dict) and not entry_store.get("_dashboard_generated"):
            await async_generate_pilotsuite_dashboard(hass, entry)
            entry_store["_dashboard_generated"] = True
            _LOGGER.info("PilotSuite dashboard auto-generated on first setup")
    except Exception:
        _LOGGER.exception("Failed to auto-generate PilotSuite dashboard")

    # Show onboarding notification on first setup (v3.12.0)
    try:
        entry_store = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
        if isinstance(entry_store, dict) and not entry_store.get("_onboarding_shown"):
            from homeassistant.components.persistent_notification import async_create
            async_create(
                hass,
                title="PilotSuite ready",
                message=(
                    "Your local AI assistant **Styx** is set up and running.\n\n"
                    "**Quick start:**\n"
                    "- Open **Settings > Voice assistants** and select **PilotSuite** as your conversation agent\n"
                    "- Use the PilotSuite dashboard for Mood, Neurons, and Habitus cards\n"
                    "- Configure Habitus zones via **Settings > Integrations > PilotSuite > Configure**\n\n"
                    "All processing runs locally on your Home Assistant — no cloud required."
                ),
                notification_id=f"pilotsuite_onboarding_{entry.entry_id}",
            )
            entry_store["_onboarding_shown"] = True
    except Exception:
        _LOGGER.debug("Onboarding notification skipped: %s", exc_info=True)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime = _get_runtime(hass)
    
    # Unload User Preference Module
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    user_pref_module = entry_data.get("user_preference_module")
    if user_pref_module:
        await user_pref_module.async_unload()
    
    # Unload Multi-User Preference Learning Module
    from .multi_user_preferences import _MUPL_MODULE_KEY
    mupl_module = entry_data.get(_MUPL_MODULE_KEY)
    if mupl_module:
        await mupl_module.async_unload()

    # Unload Zone Detector (v3.1.0)
    zone_detector = entry_data.get("zone_detector")
    if zone_detector:
        await zone_detector.async_unload()

    # Unregister conversation agent (v3.10.0)
    try:
        from .conversation import async_unload_conversation
        await async_unload_conversation(hass, entry)
    except Exception:
        _LOGGER.exception("Failed to unload conversation agent")

    # Unload agent auto-config services (v5.21.0)
    try:
        from .agent_auto_config import async_unload_agent_auto_config
        await async_unload_agent_auto_config(hass, entry)
    except Exception:
        _LOGGER.exception("Failed to unload agent auto-config")

    return await runtime.async_unload_entry(entry, modules=_MODULES)
