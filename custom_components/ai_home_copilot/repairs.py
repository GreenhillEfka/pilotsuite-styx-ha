from __future__ import annotations

import voluptuous as vol

from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant

from .storage import CandidateState, async_set_candidate_state

STEP_CHOICE = vol.Schema(
    {
        vol.Required("decision", default="imported"): vol.In(
            {
                "imported": "Blueprint importiert / Automation erstellt",
                "dismiss": "Nicht mehr vorschlagen",
            }
        )
    }
)


class CandidateRepairFlow(RepairsFlow):
    def __init__(self, hass: HomeAssistant, *, entry_id: str, candidate_id: str) -> None:
        self.hass = hass
        self._entry_id = entry_id
        self._candidate_id = candidate_id

    async def async_step_init(self, user_input=None) -> data_entry_flow.FlowResult:
        if user_input is not None:
            if user_input["decision"] == "dismiss":
                await async_set_candidate_state(
                    self.hass, self._entry_id, self._candidate_id, CandidateState.DISMISSED
                )
                return self.async_create_entry(title="", data={"result": "dismissed"})

            await async_set_candidate_state(
                self.hass, self._entry_id, self._candidate_id, CandidateState.ACCEPTED
            )
            return self.async_create_entry(title="", data={"result": "accepted"})

        return self.async_show_form(step_id="init", data_schema=STEP_CHOICE)


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict | None,
) -> RepairsFlow:
    if not data:
        raise data_entry_flow.UnknownFlow

    entry_id = data.get("entry_id")
    candidate_id = data.get("candidate_id")

    if isinstance(entry_id, str) and isinstance(candidate_id, str):
        return CandidateRepairFlow(hass, entry_id=entry_id, candidate_id=candidate_id)

    raise data_entry_flow.UnknownFlow
