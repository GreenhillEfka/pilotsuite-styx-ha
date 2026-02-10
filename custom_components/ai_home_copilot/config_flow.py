from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_MEDIA_MUSIC_PLAYERS,
    CONF_MEDIA_TV_PLAYERS,
    CONF_SEED_ALLOWED_DOMAINS,
    CONF_SEED_BLOCKED_DOMAINS,
    CONF_SEED_MAX_OFFERS_PER_HOUR,
    CONF_SEED_MAX_OFFERS_PER_UPDATE,
    CONF_SEED_MIN_SECONDS_BETWEEN_OFFERS,
    CONF_SUGGESTION_SEED_ENTITIES,
    CONF_TEST_LIGHT,
    CONF_TOKEN,
    CONF_WEBHOOK_URL,
    CONF_WATCHDOG_ENABLED,
    CONF_WATCHDOG_INTERVAL_SECONDS,
    CONF_DEVLOG_PUSH_ENABLED,
    CONF_DEVLOG_PUSH_INTERVAL_SECONDS,
    CONF_DEVLOG_PUSH_PATH,
    CONF_DEVLOG_PUSH_MAX_LINES,
    CONF_DEVLOG_PUSH_MAX_CHARS,
    CONF_EVENTS_FORWARDER_ENABLED,
    CONF_EVENTS_FORWARDER_FLUSH_INTERVAL_SECONDS,
    CONF_EVENTS_FORWARDER_MAX_BATCH,
    CONF_EVENTS_FORWARDER_FORWARD_CALL_SERVICE,
    CONF_EVENTS_FORWARDER_IDEMPOTENCY_TTL_SECONDS,
    CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_ENABLED,
    CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_MAX_SIZE,
    CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_FLUSH_INTERVAL_SECONDS,
    CONF_HA_ERRORS_DIGEST_ENABLED,
    CONF_HA_ERRORS_DIGEST_INTERVAL_SECONDS,
    CONF_HA_ERRORS_DIGEST_MAX_LINES,
    CONF_PILOTSUITE_SHOW_SAFETY_BACKUP_BUTTONS,
    CONF_PILOTSUITE_SHOW_DEV_SURFACE_BUTTONS,
    CONF_PILOTSUITE_SHOW_GRAPH_BRIDGE_BUTTONS,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_MEDIA_MUSIC_PLAYERS,
    DEFAULT_MEDIA_TV_PLAYERS,
    DEFAULT_SEED_ALLOWED_DOMAINS,
    DEFAULT_SEED_BLOCKED_DOMAINS,
    DEFAULT_SEED_MAX_OFFERS_PER_HOUR,
    DEFAULT_SEED_MAX_OFFERS_PER_UPDATE,
    DEFAULT_SEED_MIN_SECONDS_BETWEEN_OFFERS,
    DEFAULT_SUGGESTION_SEED_ENTITIES,
    DEFAULT_TEST_LIGHT,
    DEFAULT_WATCHDOG_ENABLED,
    DEFAULT_MEDIA_MUSIC_PLAYERS,
    DEFAULT_MEDIA_TV_PLAYERS,
    DEFAULT_WATCHDOG_INTERVAL_SECONDS,
    DEFAULT_DEVLOG_PUSH_ENABLED,
    DEFAULT_DEVLOG_PUSH_INTERVAL_SECONDS,
    DEFAULT_DEVLOG_PUSH_PATH,
    DEFAULT_DEVLOG_PUSH_MAX_LINES,
    DEFAULT_DEVLOG_PUSH_MAX_CHARS,
    DEFAULT_EVENTS_FORWARDER_ENABLED,
    DEFAULT_EVENTS_FORWARDER_FLUSH_INTERVAL_SECONDS,
    DEFAULT_EVENTS_FORWARDER_MAX_BATCH,
    DEFAULT_EVENTS_FORWARDER_FORWARD_CALL_SERVICE,
    DEFAULT_EVENTS_FORWARDER_IDEMPOTENCY_TTL_SECONDS,
    DEFAULT_EVENTS_FORWARDER_PERSISTENT_QUEUE_ENABLED,
    DEFAULT_EVENTS_FORWARDER_PERSISTENT_QUEUE_MAX_SIZE,
    DEFAULT_EVENTS_FORWARDER_PERSISTENT_QUEUE_FLUSH_INTERVAL_SECONDS,
    DEFAULT_HA_ERRORS_DIGEST_ENABLED,
    DEFAULT_HA_ERRORS_DIGEST_INTERVAL_SECONDS,
    DEFAULT_HA_ERRORS_DIGEST_MAX_LINES,
    DEFAULT_PILOTSUITE_SHOW_SAFETY_BACKUP_BUTTONS,
    DEFAULT_PILOTSUITE_SHOW_DEV_SURFACE_BUTTONS,
    DEFAULT_PILOTSUITE_SHOW_GRAPH_BRIDGE_BUTTONS,
    DOMAIN,
)


def _as_csv(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ",".join([v for v in value if isinstance(v, str)])
    return str(value)


def _parse_csv(value: str) -> list[str]:
    if not value:
        return []
    parts = [p.strip() for p in value.replace("\n", ",").split(",")]
    return [p for p in parts if p]


async def _validate_input(hass: HomeAssistant, data: dict) -> None:
    # Keep validation light for MVP; coordinator will mark unavailable on failures.
    return


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await _validate_input(self.hass, user_input)
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                title = f"AI Home CoPilot ({user_input[CONF_HOST]}:{user_input[CONF_PORT]})"
                return self.async_create_entry(title=title, data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_TOKEN, description={"suggested_value": "Optional: OpenClaw Gateway Auth Token"}): str,
                # Use a plain string to maximize compatibility (no selector).
                vol.Optional(CONF_TEST_LIGHT, default="", description={"suggested_value": "Optional: light.example_entity_id for connectivity test"}): str,
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, user_input: dict | None = None) -> FlowResult:
        return await self.async_step_user(user_input)


from .config_snapshot_flow import ConfigSnapshotOptionsFlow


class OptionsFlowHandler(config_entries.OptionsFlow, ConfigSnapshotOptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        # In newer HA versions, OptionsFlow has a read-only `config_entry` property.
        # Store the entry under our own attribute to stay compatible.
        self._entry = config_entry
        ConfigSnapshotOptionsFlow.__init__(self, config_entry)

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        # Top-level menu: keep settings form, add Habitus zones wizard.
        return self.async_show_menu(
            step_id="init",
            menu_options=["settings", "habitus_zones", "backup_restore"],
        )

    async def async_step_settings(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            # webhook_url is display-only; ignore if user edits it.
            user_input.pop(CONF_WEBHOOK_URL, None)

            # Normalize seed entities (comma-separated list -> list[str])
            seed_csv = user_input.get(CONF_SUGGESTION_SEED_ENTITIES)
            if isinstance(seed_csv, str):
                user_input[CONF_SUGGESTION_SEED_ENTITIES] = _parse_csv(seed_csv)

            # Normalize media players (comma-separated list -> list[str])
            music_csv = user_input.get(CONF_MEDIA_MUSIC_PLAYERS)
            if isinstance(music_csv, str):
                user_input[CONF_MEDIA_MUSIC_PLAYERS] = _parse_csv(music_csv)

            tv_csv = user_input.get(CONF_MEDIA_TV_PLAYERS)
            if isinstance(tv_csv, str):
                user_input[CONF_MEDIA_TV_PLAYERS] = _parse_csv(tv_csv)

            # Token handling: if empty string provided, explicitly remove token
            if CONF_TOKEN in user_input:
                token = user_input.get(CONF_TOKEN, "").strip()
                if not token:  # Empty or whitespace-only = clear token
                    user_input[CONF_TOKEN] = ""

            # Keep allow/block domains as the raw string; seed adapter parses both list and str.
            return self.async_create_entry(title="", data=user_input)

        data = {**self._entry.data, **self._entry.options}

        webhook_id = data.get("webhook_id")
        base = self.hass.config.internal_url or self.hass.config.external_url or ""
        webhook_url = f"{base}/api/webhook/{webhook_id}" if webhook_id and base else (
            f"/api/webhook/{webhook_id}" if webhook_id else "(generated after first setup)"
        )

        # Token helper text
        current_token = data.get(CONF_TOKEN, "")
        token_hint = "** AKTUELL GESETZT **" if current_token else "Leer lassen um Token zu löschen"
        
        schema = vol.Schema(
            {
                vol.Optional(CONF_WEBHOOK_URL, default=webhook_url): str,
                vol.Required(CONF_HOST, default=data.get(CONF_HOST, DEFAULT_HOST)): str,
                vol.Required(CONF_PORT, default=data.get(CONF_PORT, DEFAULT_PORT)): int,
                vol.Optional(CONF_TOKEN, default="", description={"suggested_value": token_hint}): str,
                vol.Optional(CONF_TEST_LIGHT, default=data.get(CONF_TEST_LIGHT, "")): str,
                vol.Optional(
                    CONF_MEDIA_MUSIC_PLAYERS,
                    default=_as_csv(data.get(CONF_MEDIA_MUSIC_PLAYERS, DEFAULT_MEDIA_MUSIC_PLAYERS)),
                ): str,
                vol.Optional(
                    CONF_MEDIA_TV_PLAYERS,
                    default=_as_csv(data.get(CONF_MEDIA_TV_PLAYERS, DEFAULT_MEDIA_TV_PLAYERS)),
                ): str,
                # Comma-separated list of sensor entity_ids.
                vol.Optional(
                    CONF_SUGGESTION_SEED_ENTITIES,
                    default=_as_csv(
                        data.get(CONF_SUGGESTION_SEED_ENTITIES, DEFAULT_SUGGESTION_SEED_ENTITIES)
                    ),
                ): str,
                vol.Optional(
                    CONF_SEED_ALLOWED_DOMAINS,
                    default=_as_csv(data.get(CONF_SEED_ALLOWED_DOMAINS, DEFAULT_SEED_ALLOWED_DOMAINS)),
                ): str,
                vol.Optional(
                    CONF_SEED_BLOCKED_DOMAINS,
                    default=_as_csv(data.get(CONF_SEED_BLOCKED_DOMAINS, DEFAULT_SEED_BLOCKED_DOMAINS)),
                ): str,
                vol.Optional(
                    CONF_SEED_MAX_OFFERS_PER_HOUR,
                    default=data.get(
                        CONF_SEED_MAX_OFFERS_PER_HOUR, DEFAULT_SEED_MAX_OFFERS_PER_HOUR
                    ),
                ): int,
                vol.Optional(
                    CONF_SEED_MIN_SECONDS_BETWEEN_OFFERS,
                    default=data.get(
                        CONF_SEED_MIN_SECONDS_BETWEEN_OFFERS,
                        DEFAULT_SEED_MIN_SECONDS_BETWEEN_OFFERS,
                    ),
                ): int,
                vol.Optional(
                    CONF_SEED_MAX_OFFERS_PER_UPDATE,
                    default=data.get(
                        CONF_SEED_MAX_OFFERS_PER_UPDATE, DEFAULT_SEED_MAX_OFFERS_PER_UPDATE
                    ),
                ): int,
                vol.Optional(
                    CONF_WATCHDOG_ENABLED,
                    default=data.get(CONF_WATCHDOG_ENABLED, DEFAULT_WATCHDOG_ENABLED),
                ): bool,
                vol.Optional(
                    CONF_WATCHDOG_INTERVAL_SECONDS,
                    default=data.get(
                        CONF_WATCHDOG_INTERVAL_SECONDS, DEFAULT_WATCHDOG_INTERVAL_SECONDS
                    ),
                ): int,
                # Core API v1: HA -> Core event forwarder (opt-in, allowlist=Habitus zones).
                vol.Optional(
                    CONF_EVENTS_FORWARDER_ENABLED,
                    default=data.get(CONF_EVENTS_FORWARDER_ENABLED, DEFAULT_EVENTS_FORWARDER_ENABLED),
                ): bool,
                vol.Optional(
                    CONF_EVENTS_FORWARDER_FLUSH_INTERVAL_SECONDS,
                    default=data.get(
                        CONF_EVENTS_FORWARDER_FLUSH_INTERVAL_SECONDS,
                        DEFAULT_EVENTS_FORWARDER_FLUSH_INTERVAL_SECONDS,
                    ),
                ): int,
                vol.Optional(
                    CONF_EVENTS_FORWARDER_MAX_BATCH,
                    default=data.get(
                        CONF_EVENTS_FORWARDER_MAX_BATCH,
                        DEFAULT_EVENTS_FORWARDER_MAX_BATCH,
                    ),
                ): int,
                vol.Optional(
                    CONF_EVENTS_FORWARDER_FORWARD_CALL_SERVICE,
                    default=data.get(
                        CONF_EVENTS_FORWARDER_FORWARD_CALL_SERVICE,
                        DEFAULT_EVENTS_FORWARDER_FORWARD_CALL_SERVICE,
                    ),
                ): bool,
                vol.Optional(
                    CONF_EVENTS_FORWARDER_IDEMPOTENCY_TTL_SECONDS,
                    default=data.get(
                        CONF_EVENTS_FORWARDER_IDEMPOTENCY_TTL_SECONDS,
                        DEFAULT_EVENTS_FORWARDER_IDEMPOTENCY_TTL_SECONDS,
                    ),
                ): int,

                # Events forwarder persistent queue (optional): store unsent events across HA restarts.
                vol.Optional(
                    CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_ENABLED,
                    default=data.get(
                        CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_ENABLED,
                        DEFAULT_EVENTS_FORWARDER_PERSISTENT_QUEUE_ENABLED,
                    ),
                ): bool,
                vol.Optional(
                    CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_MAX_SIZE,
                    default=data.get(
                        CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_MAX_SIZE,
                        DEFAULT_EVENTS_FORWARDER_PERSISTENT_QUEUE_MAX_SIZE,
                    ),
                ): int,
                vol.Optional(
                    CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_FLUSH_INTERVAL_SECONDS,
                    default=data.get(
                        CONF_EVENTS_FORWARDER_PERSISTENT_QUEUE_FLUSH_INTERVAL_SECONDS,
                        DEFAULT_EVENTS_FORWARDER_PERSISTENT_QUEUE_FLUSH_INTERVAL_SECONDS,
                    ),
                ): int,

                # PilotSuite UX knobs (safe defaults).
                vol.Optional(
                    CONF_PILOTSUITE_SHOW_SAFETY_BACKUP_BUTTONS,
                    default=data.get(
                        CONF_PILOTSUITE_SHOW_SAFETY_BACKUP_BUTTONS,
                        DEFAULT_PILOTSUITE_SHOW_SAFETY_BACKUP_BUTTONS,
                    ),
                ): bool,
                vol.Optional(
                    CONF_PILOTSUITE_SHOW_DEV_SURFACE_BUTTONS,
                    default=data.get(
                        CONF_PILOTSUITE_SHOW_DEV_SURFACE_BUTTONS,
                        DEFAULT_PILOTSUITE_SHOW_DEV_SURFACE_BUTTONS,
                    ),
                ): bool,
                vol.Optional(
                    CONF_PILOTSUITE_SHOW_GRAPH_BRIDGE_BUTTONS,
                    default=data.get(
                        CONF_PILOTSUITE_SHOW_GRAPH_BRIDGE_BUTTONS,
                        DEFAULT_PILOTSUITE_SHOW_GRAPH_BRIDGE_BUTTONS,
                    ),
                ): bool,

                # Local HA log digest (opt-in): show relevant warnings/errors as notifications.
                vol.Optional(
                    CONF_HA_ERRORS_DIGEST_ENABLED,
                    default=data.get(CONF_HA_ERRORS_DIGEST_ENABLED, DEFAULT_HA_ERRORS_DIGEST_ENABLED),
                ): bool,
                vol.Optional(
                    CONF_HA_ERRORS_DIGEST_INTERVAL_SECONDS,
                    default=data.get(
                        CONF_HA_ERRORS_DIGEST_INTERVAL_SECONDS,
                        DEFAULT_HA_ERRORS_DIGEST_INTERVAL_SECONDS,
                    ),
                ): int,
                vol.Optional(
                    CONF_HA_ERRORS_DIGEST_MAX_LINES,
                    default=data.get(
                        CONF_HA_ERRORS_DIGEST_MAX_LINES,
                        DEFAULT_HA_ERRORS_DIGEST_MAX_LINES,
                    ),
                ): int,

                # Opt-in dev tool: push sanitized HA log snippets to Copilot-Core.
                vol.Optional(
                    CONF_DEVLOG_PUSH_ENABLED,
                    default=data.get(CONF_DEVLOG_PUSH_ENABLED, DEFAULT_DEVLOG_PUSH_ENABLED),
                ): bool,
                vol.Optional(
                    CONF_DEVLOG_PUSH_INTERVAL_SECONDS,
                    default=data.get(
                        CONF_DEVLOG_PUSH_INTERVAL_SECONDS,
                        DEFAULT_DEVLOG_PUSH_INTERVAL_SECONDS,
                    ),
                ): int,
                vol.Optional(
                    CONF_DEVLOG_PUSH_PATH,
                    default=data.get(CONF_DEVLOG_PUSH_PATH, DEFAULT_DEVLOG_PUSH_PATH),
                ): str,
                vol.Optional(
                    CONF_DEVLOG_PUSH_MAX_LINES,
                    default=data.get(CONF_DEVLOG_PUSH_MAX_LINES, DEFAULT_DEVLOG_PUSH_MAX_LINES),
                ): int,
                vol.Optional(
                    CONF_DEVLOG_PUSH_MAX_CHARS,
                    default=data.get(CONF_DEVLOG_PUSH_MAX_CHARS, DEFAULT_DEVLOG_PUSH_MAX_CHARS),
                ): int,
            }
        )

        return self.async_show_form(step_id="settings", data_schema=schema)

    async def async_step_habitus_zones(self, user_input: dict | None = None) -> FlowResult:
        return self.async_show_menu(
            step_id="habitus_zones",
            menu_options=["create_zone", "edit_zone", "delete_zone", "bulk_edit", "back"],
        )

    async def async_step_back(self, user_input: dict | None = None) -> FlowResult:
        return await self.async_step_init()

    async def async_step_create_zone(self, user_input: dict | None = None) -> FlowResult:
        return await self._async_step_zone_form(mode="create", user_input=user_input)

    async def async_step_edit_zone(self, user_input: dict | None = None) -> FlowResult:
        from .habitus_zones_store import async_get_zones

        zones = await async_get_zones(self.hass, self._entry.entry_id)
        ids = [z.zone_id for z in zones]
        if not ids:
            return self.async_abort(reason="no_zones")

        if user_input is None:
            schema = vol.Schema({vol.Required("zone_id"): vol.In(ids)})
            return self.async_show_form(step_id="edit_zone", data_schema=schema)

        zid = str(user_input.get("zone_id", ""))
        return await self._async_step_zone_form(mode="edit", user_input=None, zone_id=zid)

    async def async_step_delete_zone(self, user_input: dict | None = None) -> FlowResult:
        from .habitus_zones_store import async_get_zones, async_set_zones

        zones = await async_get_zones(self.hass, self._entry.entry_id)
        ids = [z.zone_id for z in zones]
        if not ids:
            return self.async_abort(reason="no_zones")

        if user_input is None:
            schema = vol.Schema({vol.Required("zone_id"): vol.In(ids)})
            return self.async_show_form(step_id="delete_zone", data_schema=schema)

        zid = str(user_input.get("zone_id", ""))
        remain = [z for z in zones if z.zone_id != zid]
        await async_set_zones(self.hass, self._entry.entry_id, remain)
        return await self.async_step_habitus_zones()

    async def async_step_bulk_edit(self, user_input: dict | None = None) -> FlowResult:
        """Bulk editor to paste YAML/JSON (no 255-char limit) with validation."""
        from homeassistant.helpers import selector
        import yaml
        import json

        from .habitus_zones_store import async_get_zones, async_set_zones_from_raw

        zones = await async_get_zones(self.hass, self._entry.entry_id)
        current = []
        for z in zones:
            # UX: if a zone has structured `entities`, prefer emitting that only.
            # Emitting both `entity_ids` + `entities` leads to confusion and duplicates.
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

                await async_set_zones_from_raw(self.hass, self._entry.entry_id, raw)
            except Exception as err:  # noqa: BLE001
                return self.async_show_form(
                    step_id="bulk_edit",
                    data_schema=vol.Schema(
                        {
                            vol.Required(
                                "zones",
                                default=raw_text,
                            ): selector.TextSelector(
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

    async def _async_step_zone_form(
        self,
        *,
        mode: str,
        user_input: dict | None,
        zone_id: str | None = None,
    ) -> FlowResult:
        from homeassistant.helpers import selector
        from .habitus_zones_store import HabitusZone, async_get_zones, async_set_zones

        zones = await async_get_zones(self.hass, self._entry.entry_id)
        existing = {z.zone_id: z for z in zones}

        if zone_id and zone_id in existing:
            z = existing[zone_id]
        else:
            z = HabitusZone(zone_id="", name="", entity_ids=[], entities=None)

        if user_input is not None:
            zid = str(user_input.get("zone_id") or "").strip()
            name = str(user_input.get("name") or zid).strip()
            motion = str(user_input.get("motion_entity_id") or "").strip()
            lights = user_input.get("light_entity_ids") or []
            optional = user_input.get("optional_entity_ids") or []

            if not isinstance(lights, list):
                lights = [lights]
            if not isinstance(optional, list):
                optional = [optional]

            entity_ids = [motion] + [str(x).strip() for x in lights] + [str(x).strip() for x in optional]
            entity_ids = [e for e in entity_ids if e]

            # De-dupe
            seen = set()
            uniq = []
            for e in entity_ids:
                if e in seen:
                    continue
                seen.add(e)
                uniq.append(e)

            ent_map = {
                "motion": [motion] if motion else [],
                "lights": [str(x).strip() for x in lights if str(x).strip()],
                "other": [str(x).strip() for x in optional if str(x).strip()],
            }
            # drop empty roles
            ent_map = {k: v for k, v in ent_map.items() if v}

            new_zone = HabitusZone(zone_id=zid, name=name or zid, entity_ids=uniq, entities=ent_map or None)

            # Replace / insert
            new_list = [zz for zz in zones if zz.zone_id != zid]
            new_list.append(new_zone)
            # Persist (store enforces requirements)
            await async_set_zones(self.hass, self._entry.entry_id, new_list)

            return await self.async_step_habitus_zones()

        default_motion = None
        default_lights: list[str] = []
        default_optional: list[str] = []

        # Best-effort prefill from existing zone.
        ent_map = getattr(z, "entities", None)
        if isinstance(ent_map, dict):
            motion_list = ent_map.get("motion") or []
            lights_list = ent_map.get("lights") or []
            other_list = ent_map.get("other") or []

            if motion_list:
                default_motion = str(motion_list[0])
            default_lights = [str(x) for x in lights_list]
            default_optional = [str(x) for x in other_list]
        else:
            for eid in z.entity_ids:
                if eid.startswith("light."):
                    default_lights.append(eid)
                elif eid.startswith("binary_sensor.") and default_motion is None:
                    default_motion = eid
                else:
                    default_optional.append(eid)

        schema = vol.Schema(
            {
                vol.Required("zone_id", default=(z.zone_id if mode == "edit" else "")): str,
                vol.Optional("name", default=(z.name if z.name else "")): str,
                vol.Required(
                    "motion_entity_id",
                    default=default_motion or "",
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["binary_sensor", "sensor"], multiple=False)
                ),
                vol.Required(
                    "light_entity_ids",
                    default=default_lights,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="light", multiple=True)
                ),
                vol.Optional(
                    "optional_entity_ids",
                    default=default_optional,
                ): selector.EntitySelector(selector.EntitySelectorConfig(multiple=True)),
            }
        )

        step_id = "create_zone" if mode == "create" else "edit_zone_form"
        return self.async_show_form(step_id=step_id, data_schema=schema)


# Options flow is provided via ConfigFlow.async_get_options_flow
