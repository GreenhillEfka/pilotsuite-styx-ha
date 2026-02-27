"""OptionsFlowHandler for PilotSuite config entry."""
from __future__ import annotations

import json
import logging

import voluptuous as vol
import yaml

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .config_helpers import merge_config_data, parse_csv
from .core_endpoint import normalize_host_port
from .config_schema_builders import build_neuron_schema
from .config_snapshot_flow import ConfigSnapshotOptionsFlow
from .config_zones_flow import async_step_zone_form
from .config_tags_flow import async_step_add_tag, async_step_edit_tag, async_step_delete_tag
from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_TOKEN,
    CONF_TEST_LIGHT,
    CONF_WEBHOOK_URL,
    CONF_OLLAMA_HOST,
    CONF_OLLAMA_PORT,
    CONF_SEARXNG_ENABLED,
    CONF_SEARXNG_HOST,
    CONF_SEARXNG_PORT,
    DEFAULT_OLLAMA_HOST,
    DEFAULT_OLLAMA_PORT,
    DEFAULT_SEARXNG_HOST,
    DEFAULT_SEARXNG_PORT,
    CONF_MEDIA_MUSIC_PLAYERS,
    CONF_MEDIA_TV_PLAYERS,
    CONF_SUGGESTION_SEED_ENTITIES,
    CONF_EVENTS_FORWARDER_ADDITIONAL_ENTITIES,
    CONF_TRACKED_USERS,
    CONF_NEURON_CONTEXT_ENTITIES,
    CONF_NEURON_STATE_ENTITIES,
    CONF_NEURON_MOOD_ENTITIES,
    CONF_WASTE_ENTITIES,
    CONF_BIRTHDAY_CALENDAR_ENTITIES,
    CONF_PRIMARY_USER,
    CONF_WASTE_TTS_ENTITY,
    CONF_BIRTHDAY_TTS_ENTITY,
    CONF_ZONE_AUTOMATION_BRIGHTNESS_THRESHOLD,
    CONF_ZONE_AUTOMATION_GRACE_PERIOD_S,
)

_LOGGER = logging.getLogger(__name__)


def _normalize_entity_list(value: object) -> list[str]:
    """Normalize selector/csv values into list[str]."""
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return parse_csv(value)
    if value is None:
        return []
    item = str(value).strip()
    return [item] if item else []


class OptionsFlowHandler(config_entries.OptionsFlow, ConfigSnapshotOptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry
        self._editing_zone_id: str | None = None
        ConfigSnapshotOptionsFlow.__init__(self, config_entry)

    def _effective_config(self) -> dict:
        """Return merged live config (entry.data + entry.options)."""
        return merge_config_data(self._entry.data, self._entry.options)

    def _create_merged_entry(self, updates: dict) -> FlowResult:
        """Persist options without dropping unrelated keys from previous steps."""
        return self.async_create_entry(title="", data=merge_config_data(self._entry.data, self._entry.options, updates))

    async def _push_service_config_to_core(self, user_input: dict, data: dict) -> None:
        """Push Ollama/SearXNG config to Core add-on (best effort)."""
        import aiohttp
        from homeassistant.helpers.aiohttp_client import async_get_clientsession
        from .core_endpoint import build_base_url, DEFAULT_CORE_PORT

        host = str(user_input.get(CONF_HOST) or data.get(CONF_HOST, "")).strip()
        try:
            port = int(user_input.get(CONF_PORT) or data.get(CONF_PORT, DEFAULT_CORE_PORT))
        except (TypeError, ValueError):
            port = DEFAULT_CORE_PORT
        token = str(user_input.get(CONF_TOKEN) or data.get(CONF_TOKEN, "") or "").strip()
        if not host:
            return

        ollama_host = str(user_input.get(CONF_OLLAMA_HOST, DEFAULT_OLLAMA_HOST) or "").strip()
        try:
            ollama_port = int(user_input.get(CONF_OLLAMA_PORT, DEFAULT_OLLAMA_PORT))
        except (TypeError, ValueError):
            ollama_port = DEFAULT_OLLAMA_PORT
        searxng_enabled = bool(user_input.get(CONF_SEARXNG_ENABLED, False))
        searxng_host = str(user_input.get(CONF_SEARXNG_HOST, DEFAULT_SEARXNG_HOST) or "").strip()
        try:
            searxng_port = int(user_input.get(CONF_SEARXNG_PORT, DEFAULT_SEARXNG_PORT))
        except (TypeError, ValueError):
            searxng_port = DEFAULT_SEARXNG_PORT

        payload = {}
        if ollama_host:
            payload["ollama_url"] = f"http://{ollama_host}:{ollama_port}"
        if searxng_host:
            payload["searxng_enabled"] = searxng_enabled
            payload["searxng_base_url"] = f"http://{searxng_host}:{searxng_port}"

        if not payload:
            return

        base = build_base_url(host, port).rstrip("/")
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            headers["X-Auth-Token"] = token

        session = async_get_clientsession(self.hass)
        try:
            async with session.post(
                f"{base}/api/v1/config/services",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    _LOGGER.info("Pushed Ollama/SearXNG config to Core")
                else:
                    _LOGGER.debug("Core config push returned %s", resp.status)
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Could not push service config to Core (non-blocking)")

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=["connection", "modules", "habitus_zones", "entity_tags", "neurons", "backup_restore", "generate_dashboard"],
        )

    # ── Connection ───────────────────────────────────────────────────

    async def async_step_connection(self, user_input: dict | None = None) -> FlowResult:
        """Network settings: host, port, token, webhook URL, test light."""
        if user_input is not None:
            user_input.pop(CONF_WEBHOOK_URL, None)
            data = self._effective_config()
            host, port = normalize_host_port(
                user_input.get(CONF_HOST, data.get(CONF_HOST)),
                user_input.get(CONF_PORT, data.get(CONF_PORT)),
            )
            user_input[CONF_HOST] = host
            user_input[CONF_PORT] = port

            clear_token = user_input.pop("_clear_token", False)
            new_token = user_input.get(CONF_TOKEN, "")

            if clear_token:
                user_input[CONF_TOKEN] = ""
            elif not new_token:
                existing_token = str(data.get(CONF_TOKEN, "") or "")
                user_input[CONF_TOKEN] = existing_token

            if CONF_TOKEN in user_input:
                token = user_input.get(CONF_TOKEN, "").strip()
                if not token:
                    user_input[CONF_TOKEN] = ""

            # Optional selector: keep prior value when UI submits null.
            test_light = user_input.get(CONF_TEST_LIGHT)
            if test_light in (None, ""):
                existing_test_light = str(data.get(CONF_TEST_LIGHT) or "").strip()
                if existing_test_light:
                    user_input[CONF_TEST_LIGHT] = existing_test_light
                else:
                    user_input.pop(CONF_TEST_LIGHT, None)

            # Push Ollama/SearXNG config to Core (best effort, non-blocking)
            await self._push_service_config_to_core(user_input, data)

            return self._create_merged_entry(user_input)

        data = self._effective_config()

        webhook_id = data.get("webhook_id")
        base = self.hass.config.internal_url or self.hass.config.external_url or ""
        webhook_url = (
            f"{base}/api/webhook/{webhook_id}"
            if webhook_id and base
            else (f"/api/webhook/{webhook_id}" if webhook_id else "(generated after first setup)")
        )

        current_token = data.get(CONF_TOKEN, "")
        token_hint = "** SET **" if current_token else ""

        from .config_schema_builders import build_connection_schema
        schema = vol.Schema(build_connection_schema(data, webhook_url, token_hint))
        return self.async_show_form(step_id="connection", data_schema=schema)

    # ── Modules (menu) ───────────────────────────────────────────────

    async def async_step_modules(self, user_input: dict | None = None) -> FlowResult:
        """Module configuration — shows a per-module submenu."""
        return self.async_show_menu(
            step_id="modules",
            menu_options=[
                "module_media",
                "module_forwarder",
                "module_seed",
                "module_user_prefs",
                "module_waste",
                "module_birthday",
                "module_zone_automation",
                "module_ha_errors",
                "module_devlog",
                "module_watchdog",
                "module_pilotsuite_ux",
                "back",
            ],
        )

    # ── Module: Media ────────────────────────────────────────────────

    async def async_step_module_media(self, user_input: dict | None = None) -> FlowResult:
        """Media player module configuration."""
        if user_input is not None:
            for field in (CONF_MEDIA_MUSIC_PLAYERS, CONF_MEDIA_TV_PLAYERS):
                if field in user_input:
                    user_input[field] = _normalize_entity_list(user_input[field])
            return self._create_merged_entry(user_input)

        data = self._effective_config()
        from .config_schema_builders import build_media_schema
        return self.async_show_form(
            step_id="module_media",
            data_schema=vol.Schema(build_media_schema(data)),
        )

    # ── Module: Events Forwarder ─────────────────────────────────────

    async def async_step_module_forwarder(self, user_input: dict | None = None) -> FlowResult:
        """Events forwarder module configuration."""
        if user_input is not None:
            if CONF_EVENTS_FORWARDER_ADDITIONAL_ENTITIES in user_input:
                user_input[CONF_EVENTS_FORWARDER_ADDITIONAL_ENTITIES] = _normalize_entity_list(
                    user_input[CONF_EVENTS_FORWARDER_ADDITIONAL_ENTITIES]
                )
            return self._create_merged_entry(user_input)

        data = self._effective_config()
        from .config_schema_builders import build_forwarder_schema
        return self.async_show_form(
            step_id="module_forwarder",
            data_schema=vol.Schema(build_forwarder_schema(data)),
        )

    # ── Module: Suggestion Seed ──────────────────────────────────────

    async def async_step_module_seed(self, user_input: dict | None = None) -> FlowResult:
        """Suggestion seed module configuration."""
        if user_input is not None:
            if CONF_SUGGESTION_SEED_ENTITIES in user_input:
                user_input[CONF_SUGGESTION_SEED_ENTITIES] = _normalize_entity_list(
                    user_input[CONF_SUGGESTION_SEED_ENTITIES]
                )
            return self._create_merged_entry(user_input)

        data = self._effective_config()
        from .config_schema_builders import build_seed_schema
        return self.async_show_form(
            step_id="module_seed",
            data_schema=vol.Schema(build_seed_schema(data)),
        )

    # ── Module: User Preferences ─────────────────────────────────────

    async def async_step_module_user_prefs(self, user_input: dict | None = None) -> FlowResult:
        """User preferences module configuration."""
        if user_input is not None:
            if CONF_TRACKED_USERS in user_input:
                user_input[CONF_TRACKED_USERS] = _normalize_entity_list(user_input[CONF_TRACKED_USERS])
            for field in (CONF_PRIMARY_USER,):
                if field in user_input and user_input[field] is None:
                    user_input[field] = ""
            return self._create_merged_entry(user_input)

        data = self._effective_config()
        from .config_schema_builders import build_user_prefs_schema
        return self.async_show_form(
            step_id="module_user_prefs",
            data_schema=vol.Schema(build_user_prefs_schema(data)),
        )

    # ── Module: Waste Reminder ───────────────────────────────────────

    async def async_step_module_waste(self, user_input: dict | None = None) -> FlowResult:
        """Waste collection reminder module configuration."""
        if user_input is not None:
            if CONF_WASTE_ENTITIES in user_input:
                user_input[CONF_WASTE_ENTITIES] = _normalize_entity_list(user_input[CONF_WASTE_ENTITIES])
            if CONF_WASTE_TTS_ENTITY in user_input and user_input[CONF_WASTE_TTS_ENTITY] is None:
                user_input[CONF_WASTE_TTS_ENTITY] = ""
            return self._create_merged_entry(user_input)

        data = self._effective_config()
        from .config_schema_builders import build_waste_schema
        return self.async_show_form(
            step_id="module_waste",
            data_schema=vol.Schema(build_waste_schema(data)),
        )

    # ── Module: Birthday Reminder ────────────────────────────────────

    async def async_step_module_birthday(self, user_input: dict | None = None) -> FlowResult:
        """Birthday reminder module configuration."""
        if user_input is not None:
            if CONF_BIRTHDAY_CALENDAR_ENTITIES in user_input:
                user_input[CONF_BIRTHDAY_CALENDAR_ENTITIES] = _normalize_entity_list(
                    user_input[CONF_BIRTHDAY_CALENDAR_ENTITIES]
                )
            if CONF_BIRTHDAY_TTS_ENTITY in user_input and user_input[CONF_BIRTHDAY_TTS_ENTITY] is None:
                user_input[CONF_BIRTHDAY_TTS_ENTITY] = ""
            return self._create_merged_entry(user_input)

        data = self._effective_config()
        from .config_schema_builders import build_birthday_schema
        return self.async_show_form(
            step_id="module_birthday",
            data_schema=vol.Schema(build_birthday_schema(data)),
        )

    # ── Module: Zone Automation ──────────────────────────────────────

    async def async_step_module_zone_automation(self, user_input: dict | None = None) -> FlowResult:
        """Zone automation settings (brightness threshold, presence grace period)."""
        if user_input is not None:
            return self._create_merged_entry(user_input)

        data = self._effective_config()
        from .config_schema_builders import build_zone_automation_schema
        return self.async_show_form(
            step_id="module_zone_automation",
            data_schema=vol.Schema(build_zone_automation_schema(data)),
        )

    # ── Module: HA Errors Digest ─────────────────────────────────────

    async def async_step_module_ha_errors(self, user_input: dict | None = None) -> FlowResult:
        """HA error digest module configuration."""
        if user_input is not None:
            return self._create_merged_entry(user_input)

        data = self._effective_config()
        from .config_schema_builders import build_ha_errors_schema
        return self.async_show_form(
            step_id="module_ha_errors",
            data_schema=vol.Schema(build_ha_errors_schema(data)),
        )

    # ── Module: Devlog Push ──────────────────────────────────────────

    async def async_step_module_devlog(self, user_input: dict | None = None) -> FlowResult:
        """Dev log push module configuration."""
        if user_input is not None:
            return self._create_merged_entry(user_input)

        data = self._effective_config()
        from .config_schema_builders import build_devlog_schema
        return self.async_show_form(
            step_id="module_devlog",
            data_schema=vol.Schema(build_devlog_schema(data)),
        )

    # ── Module: Watchdog ─────────────────────────────────────────────

    async def async_step_module_watchdog(self, user_input: dict | None = None) -> FlowResult:
        """Watchdog module configuration."""
        if user_input is not None:
            return self._create_merged_entry(user_input)

        data = self._effective_config()
        from .config_schema_builders import build_watchdog_schema
        return self.async_show_form(
            step_id="module_watchdog",
            data_schema=vol.Schema(build_watchdog_schema(data)),
        )

    # ── Module: PilotSuite UX ────────────────────────────────────────

    async def async_step_module_pilotsuite_ux(self, user_input: dict | None = None) -> FlowResult:
        """PilotSuite UX / button visibility configuration."""
        if user_input is not None:
            return self._create_merged_entry(user_input)

        data = self._effective_config()
        from .config_schema_builders import build_pilotsuite_schema
        return self.async_show_form(
            step_id="module_pilotsuite_ux",
            data_schema=vol.Schema(build_pilotsuite_schema(data)),
        )

    # ── Habitus zones ────────────────────────────────────────────────

    async def async_step_habitus_zones(self, user_input: dict | None = None) -> FlowResult:
        return self.async_show_menu(
            step_id="habitus_zones",
            menu_options=[
                "create_zone",
                "edit_zone",
                "delete_zone",
                "suggest_zones",
                "bulk_edit",
                "dashboard_info",
                "back",
            ],
        )

    async def async_step_suggest_zones(self, user_input: dict | None = None) -> FlowResult:
        """Fetch zone suggestions from Core and let user adopt them."""
        import aiohttp
        from homeassistant.helpers.aiohttp_client import async_get_clientsession
        from .habitus_zones_store_v2 import HabitusZoneV2, async_get_zones_v2, async_set_zones_v2
        from .core_endpoint import build_base_url, DEFAULT_CORE_PORT

        config = self._effective_config()
        host = str(config.get("host", "")).strip()
        try:
            port = int(config.get("port", DEFAULT_CORE_PORT))
        except (TypeError, ValueError):
            port = DEFAULT_CORE_PORT
        token = str(config.get("token") or "").strip()

        if user_input is not None:
            selected = user_input.get("adopt_zones", [])
            if not selected:
                return await self.async_step_habitus_zones()

            suggestions = getattr(self, "_zone_suggestions", [])
            existing_zones = await async_get_zones_v2(self.hass, self._entry.entry_id)
            existing_ids = {z.zone_id for z in existing_zones}
            new_zones = list(existing_zones)

            for suggestion in suggestions:
                zid = suggestion.get("zone_id", "")
                if zid not in selected or zid in existing_ids:
                    continue

                entity_roles = suggestion.get("entity_roles", {})
                all_entity_ids = suggestion.get("recommended_entities", [])

                ent_map = {}
                for role, eids in entity_roles.items():
                    if eids:
                        ent_map[role] = tuple(eids)

                new_zone = HabitusZoneV2(
                    zone_id=zid,
                    name=suggestion.get("name", zid),
                    entity_ids=tuple(all_entity_ids),
                    entities=ent_map or None,
                    metadata={"source": "core_suggestion"},
                )
                new_zones.append(new_zone)

            try:
                await async_set_zones_v2(self.hass, self._entry.entry_id, new_zones)
                from .config_zones_flow import _sync_zones_to_core
                await _sync_zones_to_core(self.hass, config, new_zones)
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Failed to save suggested zones")

            return await self.async_step_habitus_zones()

        # Fetch suggestions from Core
        suggestions = []
        if host:
            base = build_base_url(host, port).rstrip("/")
            headers: dict[str, str] = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"
                headers["X-Auth-Token"] = token

            session = async_get_clientsession(self.hass)
            try:
                async with session.get(
                    f"{base}/api/v1/hub/habitus/management/recommendations",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        suggestions = data.get("zones", [])
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Could not fetch zone suggestions from Core")

        if not suggestions:
            return self.async_abort(reason="no_suggestions")

        self._zone_suggestions = suggestions

        existing_zones = await async_get_zones_v2(self.hass, self._entry.entry_id)
        existing_ids = {z.zone_id for z in existing_zones}

        options = []
        for s in suggestions:
            zid = s.get("zone_id", "")
            name = s.get("name", zid)
            count = s.get("recommended_count", 0)
            if zid and zid not in existing_ids:
                options.append(
                    selector.SelectOptionDict(
                        value=zid,
                        label=f"{name} ({count} entities)",
                    )
                )

        if not options:
            return self.async_abort(reason="no_new_suggestions")

        schema = vol.Schema(
            {
                vol.Required("adopt_zones"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(step_id="suggest_zones", data_schema=schema)

    async def async_step_dashboard_info(self, user_input: dict | None = None) -> FlowResult:
        """Inform users that React/Core dashboard is primary; YAML is legacy."""
        if user_input is not None:
            return await self.async_step_habitus_zones()

        schema = vol.Schema({vol.Optional("back_to_menu", default=True): bool})
        return self.async_show_form(
            step_id="dashboard_info",
            data_schema=schema,
            description_placeholders={
                "description": (
                    "PilotSuite verwendet jetzt primär das Core/React-Dashboard "
                    "für Verwaltung, Status, Habituszonen und Module.\n\n"
                    "Legacy YAML-Dashboards sind optional und standardmäßig deaktiviert. "
                    "Aktiviere sie nur bei explizitem Bedarf."
                )
            },
        )

    async def async_step_back(self, user_input: dict | None = None) -> FlowResult:
        return await self.async_step_init()

    # ── Entity Tags ─────────────────────────────────────────────────

    async def async_step_entity_tags(self, user_input: dict | None = None) -> FlowResult:
        """Show entity tags management menu."""
        return self.async_show_menu(
            step_id="entity_tags",
            menu_options=["add_tag", "edit_tag", "delete_tag", "back"],
        )

    async def async_step_add_tag(self, user_input: dict | None = None) -> FlowResult:
        return await async_step_add_tag(self, user_input)

    async def async_step_edit_tag(self, user_input: dict | None = None) -> FlowResult:
        return await async_step_edit_tag(self, user_input)

    async def async_step_delete_tag(self, user_input: dict | None = None) -> FlowResult:
        return await async_step_delete_tag(self, user_input)

    async def async_step_create_zone(self, user_input: dict | None = None) -> FlowResult:
        return await async_step_zone_form(self, mode="create", user_input=user_input)

    async def async_step_edit_zone(self, user_input: dict | None = None) -> FlowResult:
        from .habitus_zones_store_v2 import async_get_zones_v2

        zones = await async_get_zones_v2(self.hass, self._entry.entry_id)
        if not zones:
            return self.async_abort(reason="no_zones")

        if user_input is None:
            options = [
                selector.SelectOptionDict(value=z.zone_id, label=f"{z.name} ({z.zone_id})")
                for z in zones
            ]
            schema = vol.Schema(
                {
                    vol.Required("zone_id"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=options,
                            multiple=False,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            )
            return self.async_show_form(step_id="edit_zone", data_schema=schema)

        zid = str(user_input.get("zone_id", ""))
        self._editing_zone_id = zid
        return await async_step_zone_form(self, mode="edit", user_input=None, zone_id=zid)

    async def async_step_edit_zone_form(self, user_input: dict | None = None) -> FlowResult:
        """Handle the edit zone form submission."""
        zone_id = self._editing_zone_id
        if not zone_id:
            return await self.async_step_habitus_zones()
        return await async_step_zone_form(self, mode="edit", user_input=user_input, zone_id=zone_id)

    async def async_step_delete_zone(self, user_input: dict | None = None) -> FlowResult:
        from .habitus_zones_store_v2 import async_get_zones_v2, async_set_zones_v2

        zones = await async_get_zones_v2(self.hass, self._entry.entry_id)
        if not zones:
            return self.async_abort(reason="no_zones")

        if user_input is None:
            options = [
                selector.SelectOptionDict(value=z.zone_id, label=f"{z.name} ({z.zone_id})")
                for z in zones
            ]
            schema = vol.Schema(
                {
                    vol.Required("zone_id"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=options,
                            multiple=False,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            )
            return self.async_show_form(step_id="delete_zone", data_schema=schema)

        zid = str(user_input.get("zone_id", ""))
        remain = [z for z in zones if z.zone_id != zid]
        await async_set_zones_v2(self.hass, self._entry.entry_id, remain)

        # Sync deletion to Core
        try:
            from .config_zones_flow import _sync_zones_to_core
            config = self._effective_config()
            await _sync_zones_to_core(self.hass, config, remain)
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Zone sync to Core after delete failed (non-blocking)")

        return await self.async_step_habitus_zones()

    async def async_step_bulk_edit(self, user_input: dict | None = None) -> FlowResult:
        """Bulk editor to paste YAML/JSON (no 255-char limit) with validation."""
        from .habitus_zones_store_v2 import async_get_zones_v2, async_set_zones_v2_from_raw

        zones = await async_get_zones_v2(self.hass, self._entry.entry_id)
        current = []
        for z in zones:
            item = {"id": z.zone_id, "name": z.name}
            if isinstance(getattr(z, "entities", None), dict) and z.entities:
                item["entities"] = z.entities
            else:
                item["entity_ids"] = z.entity_ids
            current.append(item)

        if user_input is not None:
            raw_text = str(user_input.get("zones") or "").strip()
            if not raw_text:
                raw_text = "[]"

            try:
                try:
                    raw = json.loads(raw_text)
                except Exception:  # noqa: BLE001
                    raw = yaml.safe_load(raw_text)

                await async_set_zones_v2_from_raw(self.hass, self._entry.entry_id, raw)
            except Exception as err:  # noqa: BLE001
                return self.async_show_form(
                    step_id="bulk_edit",
                    data_schema=vol.Schema(
                        {
                            vol.Required("zones", default=raw_text): selector.TextSelector(
                                selector.TextSelectorConfig(multiline=True)
                            )
                        }
                    ),
                    errors={"base": "invalid_json"},
                    description_placeholders={"hint": f"Parse/validation error: {err}"},
                )

            # Sync to Core after bulk edit
            try:
                from .config_zones_flow import _sync_zones_to_core
                config = self._effective_config()
                all_zones = await async_get_zones_v2(self.hass, self._entry.entry_id)
                await _sync_zones_to_core(self.hass, config, all_zones)
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Zone sync to Core after bulk edit failed (non-blocking)")

            return await self.async_step_habitus_zones()

        default = yaml.safe_dump(current, allow_unicode=True, sort_keys=False)
        schema = vol.Schema(
            {
                vol.Required("zones", default=default): selector.TextSelector(
                    selector.TextSelectorConfig(multiline=True)
                )
            }
        )

        return self.async_show_form(
            step_id="bulk_edit",
            data_schema=schema,
            description_placeholders={
                "hint": (
                    "Paste a YAML/JSON list of zones (or {zones:[...]}). Each zone requires at least one valid entity_id.\n\n"
                    "Optional: use a categorized structure via `entities:` (role -> list of entity_ids), e.g.\n"
                    "- entities: {motion: [...], lights: [...], brightness: [...], heating: [...], humidity: [...], co2: [...], cover: [...], door: [...], window: [...], lock: [...], media: [...], other: [...]}"
                ),
            },
        )

    # ── Dashboard generation ─────────────────────────────────────────

    async def async_step_generate_dashboard(self, user_input: dict | None = None) -> FlowResult:
        """Generate Lovelace dashboard YAML for all Habitus zones."""
        from .habitus_dashboard import async_generate_habitus_zones_dashboard

        if user_input is not None:
            try:
                path = await async_generate_habitus_zones_dashboard(self.hass, self._entry.entry_id)
                return self.async_abort(
                    reason="dashboard_generated",
                    description_placeholders={"path": str(path)},
                )
            except Exception as err:  # noqa: BLE001
                return self.async_show_form(
                    step_id="generate_dashboard",
                    errors={"base": "generation_failed"},
                    description_placeholders={"error": str(err)},
                )

        schema = vol.Schema({vol.Optional("confirm", default=True): bool})
        return self.async_show_form(
            step_id="generate_dashboard",
            data_schema=schema,
            description_placeholders={
                "description": (
                    "Creates a Lovelace YAML dashboard file for all Habitus zones. "
                    "The file is saved in the `pilotsuite-styx/` configuration folder "
                    "(with legacy mirror in `ai_home_copilot/`)."
                )
            },
        )

    async def async_step_publish_dashboard(self, user_input: dict | None = None) -> FlowResult:
        """Publish the latest generated dashboard to www folder."""
        from .habitus_dashboard import async_publish_last_habitus_dashboard

        if user_input is not None:
            try:
                url = await async_publish_last_habitus_dashboard(self.hass)
                return self.async_abort(
                    reason="dashboard_published",
                    description_placeholders={"url": url},
                )
            except FileNotFoundError:
                return self.async_show_form(
                    step_id="publish_dashboard",
                    errors={"base": "no_dashboard_generated"},
                    description_placeholders={
                        "hint": "Generate a dashboard first using 'Generate dashboard YAML'."
                    },
                )
            except Exception as err:  # noqa: BLE001
                return self.async_show_form(
                    step_id="publish_dashboard",
                    errors={"base": "publish_failed"},
                    description_placeholders={"error": str(err)},
                )

        schema = vol.Schema({vol.Optional("confirm", default=True): bool})
        return self.async_show_form(
            step_id="publish_dashboard",
            data_schema=schema,
            description_placeholders={
                "description": (
                    "Copies the latest generated dashboard to `www/pilotsuite-styx/` "
                    "(plus legacy mirror in `www/ai_home_copilot/`) for easy download."
                )
            },
        )

    # ── Neurons ──────────────────────────────────────────────────────

    async def async_step_neurons(self, user_input: dict | None = None) -> FlowResult:
        """Configure neural system entities (auto-resolved from tags when empty)."""
        if user_input is not None:
            for field in (CONF_NEURON_CONTEXT_ENTITIES, CONF_NEURON_STATE_ENTITIES, CONF_NEURON_MOOD_ENTITIES):
                if field in user_input:
                    user_input[field] = _normalize_entity_list(user_input.get(field))

            return self._create_merged_entry(user_input)

        data = self._effective_config()

        # Auto-resolve neuron entities from tag system when not yet configured.
        try:
            from .core.modules.entity_tags_module import get_entity_tags_module, NeuronTagResolver
            tags_mod = get_entity_tags_module(self.hass, self._entry.entry_id)
            if tags_mod is not None:
                resolved = NeuronTagResolver().resolve_entities(tags_mod)
                # Only fill empty fields — user overrides take precedence.
                if not data.get(CONF_NEURON_CONTEXT_ENTITIES):
                    data[CONF_NEURON_CONTEXT_ENTITIES] = resolved["context_entities"]
                if not data.get(CONF_NEURON_STATE_ENTITIES):
                    data[CONF_NEURON_STATE_ENTITIES] = resolved["state_entities"]
                if not data.get(CONF_NEURON_MOOD_ENTITIES):
                    data[CONF_NEURON_MOOD_ENTITIES] = resolved["mood_entities"]
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Tag-based neuron auto-resolve failed (non-blocking)")

        schema = vol.Schema(build_neuron_schema(data))
        return self.async_show_form(step_id="neurons", data_schema=schema)
