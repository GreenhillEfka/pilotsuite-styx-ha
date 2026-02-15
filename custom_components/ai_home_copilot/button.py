"""AI Home CoPilot Buttons (wrapper for backward compatibility)."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_DEVLOG_PUSH_PATH,
    CONF_TEST_LIGHT,
    DEFAULT_DEVLOG_PUSH_PATH,
    DEFAULT_TEST_LIGHT,
    DOMAIN,
)
from .entity import CopilotBaseEntity
from .habitus_zones_entities import HabitusZonesValidateButton
from .habitus_zones_entities_v2 import (
    HabitusZonesV2ValidateButton,
    HabitusZonesV2SyncGraphButton,
    HabitusZonesV2ReloadButton,
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
    coordinator = data["coordinator"]
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
        # New UI buttons
        HabitusZonesValidateButton(coordinator, entry),
        HabitusZonesV2ValidateButton(coordinator, entry),
        HabitusZonesV2SyncGraphButton(coordinator, entry),
        HabitusZonesV2ReloadButton(coordinator, entry),
        CopilotTagRegistrySyncLabelsNowButton(coordinator),
        CopilotUpdateRollbackReportButton(coordinator),
        # Media Context v2 button entities
        VolumeUpButton,
        VolumeDownButton,
        VolumeMuteButton,
        ClearOverridesButton,
        # Brain dashboard summary
        CopilotBrainDashboardSummaryButton(coordinator, entry),
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


# Re-export all button classes for backward compatibility
from .button_safety_backup import (
    CopilotSafetyBackupCreateButton,
    CopilotSafetyBackupStatusButton,
)
from .button_safety import (
    CopilotRollbackLastFixButton,
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
    CopilotBrainDashboardSummaryButton,
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
)
from .button_graph import (
    CopilotPublishBrainGraphVizButton,
    CopilotPublishBrainGraphPanelButton,
)
from .button_devlog import (
    CopilotDevLogTestPushButton,
    CopilotDevLogPushLatestButton,
    CopilotDevLogsFetchButton,
)
from .button_demo import (
    CopilotCreateDemoSuggestionButton,
)
from .button_test import (
    CopilotToggleLightButton,
)
from .button_other import (
    CopilotAnalyzeLogsButton,
    CopilotHaErrorsFetchButton,
)
