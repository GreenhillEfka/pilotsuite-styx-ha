"""AI Home CoPilot Buttons (wrapper for backward compatibility)."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

from .const import (
    CONF_TEST_LIGHT,
    DEFAULT_TEST_LIGHT,
    DOMAIN,
)
from .habitus_zones_entities_v2 import (
    HabitusZonesV2ValidateButton,
    HabitusZonesV2SyncGraphButton,
    HabitusZonesV2ReloadButton,
)
from .button_camera import (
    CopilotGenerateCameraDashboardButton,
    CopilotDownloadCameraDashboardButton,
)
from .button_tag_registry import CopilotTagRegistrySyncLabelsNowButton
from .button_update_rollback import CopilotUpdateRollbackReportButton
from .button_media import (
    VolumeUpButton,
    VolumeDownButton,
    VolumeMuteButton,
    ClearOverridesButton,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data.get("coordinator")
    if coordinator is None:
        _LOGGER.error("Coordinator not available for %s, skipping button setup", entry.entry_id)
        return
    cfg = entry.data | entry.options
    
    entities = [
        # System buttons
        CopilotGenerateOverviewButton(coordinator),
        CopilotDownloadOverviewButton(coordinator),
        CopilotGenerateInventoryButton(coordinator),
        CopilotSystemHealthReportButton(coordinator),
        CopilotGenerateConfigSnapshotButton(coordinator, entry),
        CopilotDownloadConfigSnapshotButton(coordinator),
        CopilotReloadConfigEntryButton(coordinator, entry.entry_id),
        CopilotGenerateHabitusDashboardButton(coordinator, entry),
        CopilotDownloadHabitusDashboardButton(coordinator, entry),
        CopilotGeneratePilotSuiteDashboardButton(coordinator, entry),
        CopilotDownloadPilotSuiteDashboardButton(coordinator, entry),
        # Safety buttons
        CopilotSafetyBackupCreateButton(coordinator, entry),
        CopilotSafetyBackupStatusButton(coordinator, entry),
        # Debug buttons
        CopilotToggleLightButton(
            coordinator, cfg.get(CONF_TEST_LIGHT, DEFAULT_TEST_LIGHT)
        ),
        CopilotCreateDemoSuggestionButton(coordinator, entry.entry_id),
        CopilotAnalyzeLogsButton(coordinator),
        CopilotRollbackLastFixButton(coordinator),
        CopilotDevLogTestPushButton(coordinator, entry),
        CopilotDevLogPushLatestButton(coordinator, entry),
        CopilotDevLogsFetchButton(coordinator, entry),
        CopilotCoreCapabilitiesFetchButton(coordinator, entry),
        CopilotCoreEventsFetchButton(coordinator, entry),
        CopilotCoreGraphStateFetchButton(coordinator, entry),
        CopilotCoreGraphCandidatesPreviewButton(coordinator, entry),
        CopilotCoreGraphCandidatesOfferButton(coordinator, entry),
        CopilotPublishBrainGraphVizButton(coordinator, entry),
        CopilotPublishBrainGraphPanelButton(coordinator, entry),
        CopilotForwarderStatusButton(coordinator, entry),
        CopilotHaErrorsFetchButton(coordinator, entry),
        CopilotPingCoreButton(coordinator, entry),
        CopilotEnableDebug30mButton(coordinator, entry.entry_id),
        CopilotDisableDebugButton(coordinator, entry.entry_id),
        CopilotClearErrorDigestButton(coordinator, entry.entry_id),
        CopilotClearAllLogsButton(coordinator, entry.entry_id),
        # Habitus Zones v2 buttons
        HabitusZonesV2ValidateButton(coordinator, entry),
        HabitusZonesV2SyncGraphButton(coordinator, entry),
        HabitusZonesV2ReloadButton(coordinator, entry),
        CopilotTagRegistrySyncLabelsNowButton(coordinator),
        CopilotUpdateRollbackReportButton(coordinator),
        # Brain dashboard summary
        CopilotBrainDashboardSummaryButton(coordinator, entry),
        # Camera Dashboard buttons
        CopilotGenerateCameraDashboardButton(hass, entry),
        CopilotDownloadCameraDashboardButton(hass, entry),
    ]

    # Media Context v2 button entities
    media_coordinator_v2 = data.get("media_coordinator_v2") if isinstance(data, dict) else None
    if media_coordinator_v2 is not None:
        entities.extend([
            VolumeUpButton(media_coordinator_v2),
            VolumeDownButton(media_coordinator_v2),
            VolumeMuteButton(media_coordinator_v2),
            ClearOverridesButton(media_coordinator_v2),
        ])

    async_add_entities(entities, True)


# Re-export all button classes
# button_debug.py is the canonical source for debug/dev buttons
from .button_safety_backup import (
    CopilotSafetyBackupCreateButton,
    CopilotSafetyBackupStatusButton,
)
from .button_system import (
    CopilotGenerateOverviewButton,
    CopilotDownloadOverviewButton,
    CopilotGenerateInventoryButton,
    CopilotSystemHealthReportButton,
    CopilotGenerateConfigSnapshotButton,
    CopilotDownloadConfigSnapshotButton,
    CopilotReloadConfigEntryButton,
    CopilotGenerateHabitusDashboardButton,
    CopilotDownloadHabitusDashboardButton,
    CopilotGeneratePilotSuiteDashboardButton,
    CopilotDownloadPilotSuiteDashboardButton,
)
from .button_debug import (
    CopilotToggleLightButton,
    CopilotCreateDemoSuggestionButton,
    CopilotAnalyzeLogsButton,
    CopilotRollbackLastFixButton,
    CopilotDevLogTestPushButton,
    CopilotDevLogPushLatestButton,
    CopilotDevLogsFetchButton,
    CopilotCoreCapabilitiesFetchButton,
    CopilotCoreEventsFetchButton,
    CopilotCoreGraphStateFetchButton,
    CopilotCoreGraphCandidatesPreviewButton,
    CopilotCoreGraphCandidatesOfferButton,
    CopilotPublishBrainGraphVizButton,
    CopilotPublishBrainGraphPanelButton,
    CopilotForwarderStatusButton,
    CopilotHaErrorsFetchButton,
    CopilotPingCoreButton,
    CopilotEnableDebug30mButton,
    CopilotDisableDebugButton,
    CopilotClearErrorDigestButton,
    CopilotClearAllLogsButton,
    CopilotBrainDashboardSummaryButton,
)
