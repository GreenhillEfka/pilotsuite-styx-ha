from __future__ import annotations

from importlib import import_module
import logging
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_call_later

from .blueprints import async_install_blueprints
from .connection_config import merged_entry_config, resolve_core_connection_from_mapping
from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_TOKEN,
    DOMAIN,
    INTEGRATION_UNIQUE_ID,
    MAIN_DEVICE_IDENTIFIER,
)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
from .core.runtime import CopilotRuntime
from .entity import build_main_device_identifiers
from .repairs_cleanup import async_cleanup_stale_seed_repairs
from .services_setup import async_register_all_services

_LOGGER = logging.getLogger(__name__)

_LEGACY_CONNECTION_KEYS = ("core_url", "auth_token", "access_token", "api_token")
_LEGACY_TEXT_ENTITY_SUFFIXES = (
    "media_music_players_csv",
    "media_tv_players_csv",
    "seed_sensors_csv",
    "test_light_entity_id",
)
_CANONICAL_DEVICE_NAME = "PilotSuite - Styx"
_LEGACY_DEVICE_DISPLAY_NAMES = {
    "ai home copilot",
    "ai_home_copilot",
    "ai-home-copilot",
    "pilot suite",
    "pilotsuite",
}

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
    "coordinator_module": (".core.modules.coordinator_module", "CoordinatorModule"),
    "automation_adoption": (".core.modules.automation_adoption", "AutomationAdoptionModule"),
    "zone_sync": (".core.modules.zone_sync_module", "ZoneSyncModule"),
    "entity_discovery": (".core.modules.entity_discovery", "EntityDiscoveryModule"),
}

# ---------------------------------------------------------------------------
# Module Tier Classification
# ---------------------------------------------------------------------------
# Tier 0 — KERNEL: always loaded, no opt-out.  Without these, nothing works.
# Tier 1 — BRAIN:  always loaded when Core is reachable (intelligence layer).
# Tier 2 — CONTEXT: loaded when relevant HA entities are present.
# Tier 3 — EXTENSIONS: explicitly enabled by the user.
# ---------------------------------------------------------------------------
_TIER_0_KERNEL = [
    "legacy",
    "coordinator_module",
    "performance_scaling",
    "events_forwarder",
    "entity_tags",
    "brain_graph_sync",          # T0: core graph is foundational
]

_TIER_1_BRAIN = [
    "knowledge_graph_sync",
    "habitus_miner",
    "candidate_poller",
    "mood",
    "mood_context",
    "zone_sync",
    "history_backfill",
    "entity_discovery",
    "scene_module",              # T1: scene intelligence is brain-level
    "person_tracking",           # T1: household presence is brain-level
    "automation_adoption",       # T1: automation suggestions are brain-level
]

_TIER_2_CONTEXT = [
    "energy_context",
    "weather_context",
    "media_zones",
    "camera_context",
    "network",
    "ml_context",
    "voice_context",
]

_TIER_3_EXTENSIONS = [
    "homekit_bridge",
    "frigate_bridge",
    "calendar_module",
    "home_alerts",
    "character_module",
    "waste_reminder",
    "birthday_reminder",
    "dev_surface",
    "ops_runbook",
    "unifi_module",
    "quick_search",
]

# Expose tier info for dashboard / status reporting.
MODULE_TIERS: dict[str, int] = {}
for _name in _TIER_0_KERNEL:
    MODULE_TIERS[_name] = 0
for _name in _TIER_1_BRAIN:
    MODULE_TIERS[_name] = 1
for _name in _TIER_2_CONTEXT:
    MODULE_TIERS[_name] = 2
for _name in _TIER_3_EXTENSIONS:
    MODULE_TIERS[_name] = 3

# Boot order — Tier 0 first, then Tier 1, then Tier 2, then Tier 3.
_MODULES = _TIER_0_KERNEL + _TIER_1_BRAIN + _TIER_2_CONTEXT + _TIER_3_EXTENSIONS

_LEGACY_SENSOR_UNIQUE_ID_MIGRATIONS: dict[str, str] = {
    "_automation_suggestions": "copilot_automation_suggestions",
    "_comfort_index": "copilot_comfort_index",
    "_energy_cost": "copilot_energy_cost",
    "_energy_schedule": "copilot_energy_schedule",
    "_energy_sankey_flow": "copilot_energy_sankey_flow",
    "_notifications": "copilot_notifications",
}


def _as_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _legacy_yaml_dashboards_enabled(entry: ConfigEntry) -> bool:
    """Return True if Lovelace YAML dashboards should be generated/wired.

    Vision / UX: zero-config installs should have dashboards available immediately.
    Users can still disable this via the option `legacy_yaml_dashboards: false`.
    """
    cfg = merged_entry_config(entry)
    from .const import CONF_LEGACY_YAML_DASHBOARDS, DEFAULT_LEGACY_YAML_DASHBOARDS

    if CONF_LEGACY_YAML_DASHBOARDS in cfg:
        return _as_bool(cfg.get(CONF_LEGACY_YAML_DASHBOARDS), DEFAULT_LEGACY_YAML_DASHBOARDS)
    return _as_bool(os.environ.get("PILOTSUITE_LEGACY_YAML_DASHBOARDS"), DEFAULT_LEGACY_YAML_DASHBOARDS)


async def _async_migrate_entry_identity(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Migrate entry/device identity to a stable, single-instance setup."""
    entries = hass.config_entries.async_entries(DOMAIN)
    has_primary_unique = any(
        e.entry_id != entry.entry_id and e.unique_id == INTEGRATION_UNIQUE_ID for e in entries
    )
    if not entry.unique_id and not has_primary_unique:
        hass.config_entries.async_update_entry(entry, unique_id=INTEGRATION_UNIQUE_ID)
    elif not entry.unique_id and has_primary_unique:
        _LOGGER.warning(
            "Multiple PilotSuite entries detected. Entry %s kept without unique_id to avoid collision.",
            entry.entry_id,
        )

    cfg = merged_entry_config(entry)
    identifiers = build_main_device_identifiers(cfg)
    canonical_id = next((item for item in identifiers if item[1] == MAIN_DEVICE_IDENTIFIER), None)
    if canonical_id is None:
        return

    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    device = dev_reg.async_get_device(identifiers={canonical_id})
    if device is None:
        # Try legacy host:port identifier and add canonical alias when found.
        legacy_ids = {ident for ident in identifiers if ident != canonical_id}
        for legacy_id in legacy_ids:
            device = dev_reg.async_get_device(identifiers={legacy_id})
            if device is not None:
                break

    if device is None:
        # Last-resort: pick an existing PilotSuite-related device from this entry's entities.
        for entity_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
            if not entity_entry.device_id:
                continue
            probe = dev_reg.async_get(entity_entry.device_id)
            if probe is None:
                continue
            has_domain_identifier = any(ns == DOMAIN for ns, _val in probe.identifiers)
            manufacturer = str(probe.manufacturer or "").lower()
            if has_domain_identifier or manufacturer in ("pilotsuite", "ai home copilot"):
                device = probe
                break

    if device is None:
        return

    if canonical_id in device.identifiers and identifiers.issubset(set(device.identifiers)):
        return

    new_ids = set(device.identifiers)
    new_ids.update(identifiers)
    name_by_user = device.name_by_user
    if not name_by_user:
        current_name = str(getattr(device, "name", "") or "").strip().lower()
        if current_name in _LEGACY_DEVICE_DISPLAY_NAMES:
            # Promote legacy auto-generated labels to current branding without
            # touching explicit user-customized names.
            name_by_user = _CANONICAL_DEVICE_NAME

    dev_reg.async_update_device(
        device.id,
        new_identifiers=new_ids,
        manufacturer="PilotSuite",
        model="Home Assistant Integration",
        name_by_user=name_by_user,
    )

    # Consolidate entities from legacy PilotSuite devices into the canonical hub.
    for entity_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        if not entity_entry.device_id or entity_entry.device_id == device.id:
            continue
        probe = dev_reg.async_get(entity_entry.device_id)
        if probe is None:
            continue
        if not any(ns == DOMAIN for ns, _val in probe.identifiers):
            continue
        ent_reg.async_update_entity(entity_entry.entity_id, new_device_id=device.id)

    # Remove stale legacy PilotSuite devices that no longer have entities attached.
    # This keeps the device list stable across updates/migrations.
    try:
        attached_device_ids = {
            e.device_id
            for e in er.async_entries_for_config_entry(ent_reg, entry.entry_id)
            if e.device_id
        }
        remove_device = getattr(dev_reg, "async_remove_device", None)
        devices = getattr(dev_reg, "devices", None)
        removed_orphans = 0
        if callable(remove_device) and isinstance(devices, dict):
            for probe in list(devices.values()):
                if probe.id == device.id:
                    continue
                if probe.id in attached_device_ids:
                    continue
                config_entries = set(getattr(probe, "config_entries", set()) or set())
                if entry.entry_id not in config_entries:
                    continue
                identifiers = set(getattr(probe, "identifiers", set()) or set())
                if not identifiers or not any(ns == DOMAIN for ns, _ in identifiers):
                    continue
                # Be conservative: only auto-remove pure PilotSuite devices.
                if any(ns != DOMAIN for ns, _ in identifiers):
                    continue
                if remove_device(probe.id):
                    removed_orphans += 1
        if removed_orphans:
            _LOGGER.info("Removed %d orphaned PilotSuite legacy devices", removed_orphans)
    except Exception:
        _LOGGER.debug("Could not clean up orphaned legacy devices", exc_info=True)


async def _async_migrate_legacy_sensor_unique_ids(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Migrate legacy host:port based unique_ids to stable IDs."""
    ent_reg = er.async_get(hass)
    entries = er.async_entries_for_config_entry(ent_reg, entry.entry_id)

    for entity_entry in entries:
        current_unique_id = str(entity_entry.unique_id or "")
        if not current_unique_id:
            continue

        replacement: str | None = None
        for legacy_suffix, stable_unique_id in _LEGACY_SENSOR_UNIQUE_ID_MIGRATIONS.items():
            if current_unique_id == stable_unique_id:
                replacement = None
                break
            if current_unique_id.endswith(legacy_suffix):
                replacement = stable_unique_id
                break

        if replacement is None:
            continue

        existing_entity_id = ent_reg.async_get_entity_id(
            entity_entry.domain,
            DOMAIN,
            replacement,
        )
        if existing_entity_id and existing_entity_id != entity_entry.entity_id:
            _LOGGER.warning(
                "Skipping unique_id migration for %s -> %s (already used by %s)",
                entity_entry.entity_id,
                replacement,
                existing_entity_id,
            )
            continue

        ent_reg.async_update_entity(
            entity_entry.entity_id,
            new_unique_id=replacement,
        )


async def _async_migrate_connection_config(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Normalize host/port/token from data+options into canonical keys."""
    # Prefer entry.data for canonical connection values.
    # Older releases may have stale host/port/token in entry.options, and
    # merged_entry_config() gives options precedence.
    data_map = dict(entry.data) if isinstance(entry.data, dict) else {}
    options_map = dict(entry.options) if isinstance(entry.options, dict) else {}
    preferred = dict(options_map)
    preferred.update(data_map)
    host, port, token = resolve_core_connection_from_mapping(preferred)

    new_data = dict(data_map)
    new_options = dict(options_map)
    data_changed = False
    options_changed = False

    if new_data.get(CONF_HOST) != host:
        new_data[CONF_HOST] = host
        data_changed = True
    if new_data.get(CONF_PORT) != port:
        new_data[CONF_PORT] = port
        data_changed = True
    if str(new_data.get(CONF_TOKEN, "") or "").strip() != token:
        new_data[CONF_TOKEN] = token
        data_changed = True

    if new_options.get(CONF_HOST) != host:
        new_options[CONF_HOST] = host
        options_changed = True
    if new_options.get(CONF_PORT) != port:
        new_options[CONF_PORT] = port
        options_changed = True
    if str(new_options.get(CONF_TOKEN, "") or "").strip() != token:
        new_options[CONF_TOKEN] = token
        options_changed = True

    for legacy_key in _LEGACY_CONNECTION_KEYS:
        if legacy_key in new_data:
            new_data.pop(legacy_key, None)
            data_changed = True
        if legacy_key in new_options:
            new_options.pop(legacy_key, None)
            options_changed = True

    if not data_changed and not options_changed:
        return

    hass.config_entries.async_update_entry(entry, data=new_data, options=new_options)
    _LOGGER.info(
        "Normalized PilotSuite connection config for %s to %s:%s (data_changed=%s, options_changed=%s)",
        entry.entry_id,
        host,
        port,
        data_changed,
        options_changed,
    )


async def _async_cleanup_legacy_config_text_entities(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Remove obsolete config text entities that were replaced by selectors."""
    ent_reg = er.async_get(hass)
    entries = er.async_entries_for_config_entry(ent_reg, entry.entry_id)
    removed = 0

    for entity_entry in entries:
        if entity_entry.domain != "text":
            continue
        uid = str(entity_entry.unique_id or "").lower()
        eid = str(entity_entry.entity_id or "").lower()
        if not any(uid.endswith(suffix) or eid.endswith(suffix) for suffix in _LEGACY_TEXT_ENTITY_SUFFIXES):
            continue
        ent_reg.async_remove(entity_entry.entity_id)
        removed += 1

    if removed:
        _LOGGER.info("Removed %d obsolete PilotSuite legacy text entities", removed)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    async_register_all_services(hass)

    # Register Quick Search services (best-effort)
    try:
        from .search_integration import async_register_services as register_search_services
        await register_search_services(hass)
    except Exception:
        _LOGGER.exception("Failed to register quick search services")
    
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
    try:
        await _async_migrate_connection_config(hass, entry)
    except Exception:
        _LOGGER.exception("Failed to normalize connection config")

    try:
        await _async_migrate_entry_identity(hass, entry)
    except Exception:
        _LOGGER.exception("Failed to migrate entry/device identity")

    try:
        await _async_migrate_legacy_sensor_unique_ids(hass, entry)
    except Exception:
        _LOGGER.exception("Failed to migrate legacy sensor unique_ids")

    try:
        await _async_cleanup_legacy_config_text_entities(hass, entry)
    except Exception:
        _LOGGER.exception("Failed to clean up legacy config text entities")

    try:
        await async_cleanup_stale_seed_repairs(hass, entry.entry_id)
    except Exception:
        _LOGGER.exception("Failed to clean up stale seed repair issues")

    try:
        await async_install_blueprints(hass)
    except Exception:
        _LOGGER.exception("Failed to install blueprints during setup")

    runtime = _get_runtime(hass)
    try:
        await runtime.async_setup_entry(entry, modules=_MODULES)
    except Exception:
        _LOGGER.exception("Runtime setup failed")
    
    # Set up User Preference Module separately (not a CopilotModule)
    try:
        from .user_preference_module import UserPreferenceModule
        from .const import CONF_USER_PREFERENCE_ENABLED

        config = merged_entry_config(entry)
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

        config = merged_entry_config(entry)
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

    # Auto-setup: create zones and tags from HA areas (first run only)
    auto_setup_summary: dict | None = None
    try:
        from .auto_setup import async_run_auto_setup
        entry_store = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
        if isinstance(entry_store, dict) and not entry_store.get("_auto_setup_done"):
            auto_setup_summary = await async_run_auto_setup(hass, entry)
            entry_store["_auto_setup_done"] = True
            _LOGGER.info("Auto-setup completed: %s", auto_setup_summary)
    except Exception:
        _LOGGER.exception("Auto-setup failed (non-critical)")

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

    # Register PilotSuite sidebar panel (v10.4.0)
    try:
        from .panel_setup import async_setup_panel
        await async_setup_panel(hass, entry)
    except Exception:
        _LOGGER.exception("Failed to register PilotSuite sidebar panel")

    legacy_yaml_dashboards = _legacy_yaml_dashboards_enabled(entry)

    if legacy_yaml_dashboards:
        # Auto-generate dashboard YAML files on first setup (legacy mode).
        try:
            from .dashboard_wiring import async_ensure_lovelace_dashboard_wiring
            from .habitus_dashboard import async_generate_habitus_zones_dashboard
            from .pilotsuite_dashboard import async_generate_pilotsuite_dashboard

            entry_store = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
            if isinstance(entry_store, dict) and not entry_store.get("_dashboards_generated"):
                await async_generate_pilotsuite_dashboard(hass, entry, notify=False)
                await async_generate_habitus_zones_dashboard(hass, entry.entry_id, notify=False)
                wiring_state = await async_ensure_lovelace_dashboard_wiring(hass)
                entry_store["_dashboards_generated"] = True
                _LOGGER.info(
                    "PilotSuite dashboards auto-generated on first setup (legacy_yaml=true, wiring=%s)",
                    wiring_state,
                )
        except Exception:
            _LOGGER.exception("Failed to auto-generate PilotSuite dashboards")
    else:
        _LOGGER.info(
            "Legacy YAML dashboards disabled (React dashboard is primary). "
            "Set option/env legacy_yaml_dashboards=true to re-enable."
        )

    if legacy_yaml_dashboards:
        # Keep dashboard YAML updated when Habitus zones change (legacy mode).
        try:
            from .habitus_zones_store_v2 import SIGNAL_HABITUS_ZONES_V2_UPDATED
            from .habitus_dashboard import async_generate_habitus_zones_dashboard
            from .pilotsuite_dashboard import async_generate_pilotsuite_dashboard

            entry_store = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
            if isinstance(entry_store, dict):
                async def _async_refresh_dashboard(reason: str) -> None:
                    try:
                        await async_generate_pilotsuite_dashboard(hass, entry, notify=False)
                        await async_generate_habitus_zones_dashboard(hass, entry.entry_id, notify=False)
                        _LOGGER.info("PilotSuite dashboards auto-regenerated (%s)", reason)
                    except Exception:
                        _LOGGER.exception("Failed to auto-regenerate PilotSuite dashboards (%s)", reason)

                @callback
                def _schedule_dashboard_refresh(reason: str) -> None:
                    cancel = entry_store.pop("_dashboard_refresh_cancel", None)
                    if callable(cancel):
                        cancel()

                    @callback
                    def _run_refresh(_now) -> None:
                        entry_store.pop("_dashboard_refresh_cancel", None)
                        hass.async_create_task(_async_refresh_dashboard(reason))

                    # Debounce rapid zone edits to a single regen.
                    entry_store["_dashboard_refresh_cancel"] = async_call_later(hass, 2.0, _run_refresh)

                @callback
                def _on_zones_updated(updated_entry_id: str) -> None:
                    if str(updated_entry_id) != entry.entry_id:
                        return
                    _schedule_dashboard_refresh("habitus_zones_updated")

                unsub = async_dispatcher_connect(
                    hass,
                    SIGNAL_HABITUS_ZONES_V2_UPDATED,
                    _on_zones_updated,
                )
                entry_store["_dashboard_zones_unsub"] = unsub
        except Exception:
            _LOGGER.exception("Failed to set up dashboard auto-refresh listener")

    # Show onboarding notification on first setup (v3.12.0, enhanced v10.3.0)
    try:
        entry_store = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
        if isinstance(entry_store, dict) and not entry_store.get("_onboarding_shown"):
            from homeassistant.components.persistent_notification import async_create

            # Build auto-setup summary lines if available
            setup_lines = ""
            if auto_setup_summary and isinstance(auto_setup_summary, dict):
                zones_n = auto_setup_summary.get("zones_created", 0)
                tagged_n = auto_setup_summary.get("entities_tagged", 0)
                assigned_n = auto_setup_summary.get("entities_assigned", 0)
                if zones_n or tagged_n:
                    setup_lines = (
                        "\n**Auto-setup results:**\n"
                        f"- {zones_n} Habitus zone(s) created from your HA areas\n"
                        f"- {assigned_n} entit(ies) assigned to zones\n"
                        f"- {tagged_n} entit(ies) auto-tagged by domain\n\n"
                    )

            async_create(
                hass,
                title="PilotSuite — Styx is ready",
                message=(
                    "Your local AI assistant **Styx** is set up and running.\n"
                    f"{setup_lines}"
                    "**Getting started (step by step):**\n\n"
                    "1. **Set Styx as your conversation agent**\n"
                    "   Go to **Settings > Voice assistants** and select **PilotSuite — Styx**.\n\n"
                    "2. **Review your Habitus zones**\n"
                    "   Open **[Settings > Integrations > PilotSuite > Configure]"
                    f"(/config/integrations/integration/{DOMAIN})** "
                    "and select **Habitus zones**. "
                    "Zones were auto-created from your HA areas — review and adjust as needed.\n\n"
                    "3. **Check entity tags**\n"
                    "   In the same options flow, select **Entity tags** to see which entities "
                    "were automatically tagged by domain (lights, sensors, media, etc.).\n\n"
                    "4. **Open the PilotSuite Core dashboard**\n"
                    "   Navigate to the **PilotSuite** panel in the sidebar or visit "
                    "[the Core add-on](/hassio/ingress/copilot_core) "
                    "for the full management UI with Brain Graph, Mood Engine, and more.\n\n"
                    "5. **Fine-tune modules**\n"
                    "   Back in **Configure**, explore **Modules** to enable/disable features "
                    "like mood tracking, waste reminders, energy context, and more.\n\n"
                    "All processing runs **locally** on your Home Assistant — no cloud required."
                ),
                notification_id=f"pilotsuite_onboarding_{entry.entry_id}",
            )
            entry_store["_onboarding_shown"] = True
    except Exception:
        _LOGGER.debug("Onboarding notification skipped", exc_info=True)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime = _get_runtime(hass)
    
    # Unload User Preference Module
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})

    cancel_dashboard_refresh = entry_data.pop("_dashboard_refresh_cancel", None)
    if callable(cancel_dashboard_refresh):
        cancel_dashboard_refresh()

    unsub_dashboard_listener = entry_data.pop("_dashboard_zones_unsub", None)
    if callable(unsub_dashboard_listener):
        unsub_dashboard_listener()

    user_pref_module = entry_data.get("user_preference_module")
    if user_pref_module:
        await user_pref_module.async_unload()

    # Remove PilotSuite sidebar panel (v10.4.0)
    try:
        from .panel_setup import async_remove_panel_entry
        await async_remove_panel_entry(hass)
    except Exception:
        _LOGGER.debug("Could not remove PilotSuite sidebar panel", exc_info=True)

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

    result = await runtime.async_unload_entry(entry, modules=_MODULES)
    return bool(result)
