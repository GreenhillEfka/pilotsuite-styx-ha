from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.components import persistent_notification

from .const import DOMAIN
from .entity import CopilotBaseEntity


class CopilotForwarderStatusButton(CopilotBaseEntity, ButtonEntity):
    _attr_has_entity_name = False
    _attr_name = "AI Home CoPilot forwarder status"
    _attr_unique_id = "ai_home_copilot_forwarder_status"
    _attr_icon = "mdi:transit-connection-variant"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry

    async def async_press(self) -> None:
        data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id)
        if not isinstance(data, dict):
            msg = "No entry data found."
        else:
            sub = data.get("events_forwarder_subscribed")
            last = data.get("events_forwarder_last")
            seen = data.get("events_forwarder_seen")
            qlen = data.get("events_forwarder_queue_len")

            persisted_enabled = data.get("events_forwarder_persistent_enabled")
            persisted_qlen = data.get("events_forwarder_persistent_queue_len")
            drops = data.get("events_forwarder_dropped_total")
            persisted_at = data.get("events_forwarder_persisted_at")

            msg_lines = []
            if isinstance(sub, dict):
                msg_lines.append(
                    f"subscribed: {sub.get('count')} entities @ {sub.get('time')}"
                )
            else:
                msg_lines.append("subscribed: (unknown)")

            if isinstance(seen, dict):
                msg_lines.append(
                    "last seen: "
                    + f"{seen.get('time')} entity={seen.get('entity_id')} old={seen.get('old_state')} new={seen.get('new_state')} zones={seen.get('zones')}"
                )
            else:
                msg_lines.append("last seen: (none)")

            if qlen is not None:
                msg_lines.append(f"queue_len: {qlen}")

            if persisted_enabled is not None:
                msg_lines.append(f"persistent_queue: {bool(persisted_enabled)}")
            if persisted_qlen is not None:
                msg_lines.append(f"persisted_queue_len: {persisted_qlen}")
            if drops is not None:
                msg_lines.append(f"drops_total: {drops}")
            if persisted_at:
                msg_lines.append(f"persisted_at: {persisted_at}")

            if isinstance(last, dict):
                msg_lines.append(f"last send: sent={last.get('sent')} @ {last.get('time')}")
                if last.get("error"):
                    msg_lines.append(f"error: {last.get('error')}")
            else:
                msg_lines.append("last send: (none)")

            msg = "\n".join(msg_lines)

        persistent_notification.async_create(
            self.hass,
            msg,
            title="AI Home CoPilot forwarder status",
            notification_id="ai_home_copilot_forwarder_status",
        )
