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
        ConfigSnapshotOptionsFlow.__init__(self, config_entry)

    def _effective_config(self) -> dict:
        """Return merged live config (entry.data + entry.options)."""
        return merge_config_data(self._entry.data, self._entry.options)

    def _create_merged_entry(self, updates: dict) -> FlowResult:
        """Persist options without dropping unrelated keys from previous steps."""
        return self.async_create_entry(title="", data=merge_config_data(self._entry.data, self._entry.options, updates))

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=["connection", "modules", "habitus_zones", "entity_tags", "neurons", "backup_restore"],
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

    # ── Modules ──────────────────────────────────────────────────────

    async def async_step_modules(self, user_input: dict | None = None) -> FlowResult:
        """Module toggles and settings."""
        if user_input is not None:
            # Normalize entity-selection fields (selectors + backward-compatible csv).
            for field in (
                CONF_SUGGESTION_SEED_ENTITIES,
                CONF_MEDIA_MUSIC_PLAYERS,
                CONF_MEDIA_TV_PLAYERS,
                CONF_EVENTS_FORWARDER_ADDITIONAL_ENTITIES,
                CONF_TRACKED_USERS,
                CONF_WASTE_ENTITIES,
                CONF_BIRTHDAY_CALENDAR_ENTITIES,
            ):
                if field in user_input:
                    user_input[field] = _normalize_entity_list(user_input.get(field))

            # Normalize optional single-entity selectors.
            for field in (CONF_PRIMARY_USER, CONF_WASTE_TTS_ENTITY, CONF_BIRTHDAY_TTS_ENTITY):
                if field in user_input and user_input[field] is None:
                    user_input[field] = ""

            return self._create_merged_entry(user_input)

        data = self._effective_config()
        from .config_schema_builders import build_modules_schema
        schema = vol.Schema(build_modules_schema(data))
        return self.async_show_form(step_id="modules", data_schema=schema)

    # ── Habitus zones ────────────────────────────────────────────────

    async def async_step_habitus_zones(self, user_input: dict | None = None) -> FlowResult:
        return self.async_show_menu(
            step_id="habitus_zones",
            menu_options=[
                "create_zone",
                "edit_zone",
                "delete_zone",
                "generate_dashboard",
                "publish_dashboard",
                "bulk_edit",
                "back",
            ],
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
        return await async_step_zone_form(self, mode="edit", user_input=None, zone_id=zid)

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
                    "Paste a YAML/JSON list of zones (or {zones:[...]}). Each zone requires motion/presence + light.\n\n"
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
        """Configure neural system entities."""
        if user_input is not None:
            for field in (CONF_NEURON_CONTEXT_ENTITIES, CONF_NEURON_STATE_ENTITIES, CONF_NEURON_MOOD_ENTITIES):
                if field in user_input:
                    user_input[field] = _normalize_entity_list(user_input.get(field))

            return self._create_merged_entry(user_input)

        data = self._effective_config()
        schema = vol.Schema(build_neuron_schema(data))
        return self.async_show_form(step_id="neurons", data_schema=schema)
