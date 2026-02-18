"""Debug and dev buttons (split into modules)."""
from __future__ import annotations

from .button_debug_brain import (
    CopilotBrainDashboardSummaryButton,
    CopilotBrainGraphPanelVizButton,
    CopilotPublishBrainGraphPanelButton,
    CopilotPublishBrainGraphVizButton,
)
from .button_debug_core import (
    CopilotCoreCapabilitiesFetchButton,
    CopilotCoreEventsFetchButton,
    CopilotCoreGraphCandidatesOfferButton,
    CopilotCoreGraphCandidatesPreviewButton,
    CopilotCoreGraphStateFetchButton,
    CopilotPingCoreButton,
)
from .button_debug_debug_controls import (
    CopilotClearAllLogsButton,
    CopilotClearErrorDigestButton,
    CopilotDisableDebugButton,
    CopilotEnableDebug30mButton,
)
from .button_debug_forwarder import CopilotForwarderStatusButton
from .button_debug_ha_errors import CopilotHaErrorsFetchButton
from .button_debug_logs import (
    CopilotAnalyzeLogsButton,
    CopilotDevLogPushLatestButton,
    CopilotDevLogTestPushButton,
    CopilotDevLogsFetchButton,
    CopilotRollbackLastFixButton,
)
from .button_debug_misc import CopilotCreateDemoSuggestionButton, CopilotToggleLightButton


__all__ = [
    "CopilotToggleLightButton",
    "CopilotCreateDemoSuggestionButton",
    "CopilotAnalyzeLogsButton",
    "CopilotRollbackLastFixButton",
    "CopilotDevLogTestPushButton",
    "CopilotDevLogPushLatestButton",
    "CopilotDevLogsFetchButton",
    "CopilotCoreCapabilitiesFetchButton",
    "CopilotCoreEventsFetchButton",
    "CopilotCoreGraphStateFetchButton",
    "CopilotCoreGraphCandidatesPreviewButton",
    "CopilotCoreGraphCandidatesOfferButton",
    "CopilotPublishBrainGraphVizButton",
    "CopilotPublishBrainGraphPanelButton",
    "CopilotBrainGraphPanelVizButton",
    "CopilotForwarderStatusButton",
    "CopilotHaErrorsFetchButton",
    "CopilotPingCoreButton",
    "CopilotEnableDebug30mButton",
    "CopilotDisableDebugButton",
    "CopilotClearErrorDigestButton",
    "CopilotClearAllLogsButton",
    "CopilotBrainDashboardSummaryButton",
]
