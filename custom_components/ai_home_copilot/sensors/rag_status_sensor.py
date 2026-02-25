"""RAG status sensors for PilotSuite."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity


class RagPipelineStatusSensor(CoordinatorEntity, SensorEntity):
    """Expose Core RAG pipeline status."""

    _attr_name = "PilotSuite RAG Pipeline"
    _attr_unique_id = "ai_home_copilot_rag_pipeline"
    _attr_icon = "mdi:database-search"
    _attr_should_poll = False

    @property
    def native_value(self) -> str:
        data = self.coordinator.data or {}
        rag = data.get("rag_status", {}) if isinstance(data, dict) else {}
        if not isinstance(rag, dict) or not rag:
            return "offline"
        if rag.get("ok") is False:
            return "error"
        if int(rag.get("chunk_count", 0)) > 0:
            return "active"
        return "ready"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        rag = data.get("rag_status", {}) if isinstance(data, dict) else {}
        if not isinstance(rag, dict):
            rag = {}
        return {
            "document_count": int(rag.get("document_count", 0)),
            "chunk_count": int(rag.get("chunk_count", 0)),
            "default_chunk_size": rag.get("default_chunk_size"),
            "default_chunk_overlap": rag.get("default_chunk_overlap"),
            "default_threshold": rag.get("default_threshold"),
            "entry_type": rag.get("entry_type", "rag_document"),
        }
