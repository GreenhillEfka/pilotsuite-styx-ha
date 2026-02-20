from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.components import persistent_notification
from homeassistant.helpers.entity import EntityCategory

from .entity import CopilotBaseEntity
from .tag_registry import async_sync_labels_now


class CopilotTagRegistrySyncLabelsNowButton(CopilotBaseEntity, ButtonEntity):
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = False
    _attr_name = "PilotSuite tag registry sync labels now"
    _attr_unique_id = "ai_home_copilot_tag_registry_sync_labels_now"
    _attr_icon = "mdi:tag-sync"

    async def async_press(self) -> None:
        rep = await async_sync_labels_now(self.hass)

        lines = [
            f"imported_user_aliases: {rep.imported_user_aliases}",
            f"created_labels: {rep.created_labels}",
            f"updated_subjects: {rep.updated_subjects}",
            f"skipped_pending: {rep.skipped_pending}",
        ]
        if rep.errors:
            lines.append("")
            lines.append("errors:")
            for e in rep.errors:
                lines.append(f"- {e}")

        persistent_notification.async_create(
            self.hass,
            "\n".join(lines),
            title="PilotSuite Tag Registry",
            notification_id="ai_home_copilot_tag_registry",
        )
