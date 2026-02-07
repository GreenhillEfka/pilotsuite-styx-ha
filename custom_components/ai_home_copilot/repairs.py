from __future__ import annotations

import voluptuous as vol

from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant

from .log_fixer import async_disable_custom_integration_for_manifest_error
from .log_store import FindingType
from .log_store import async_get_log_fixer_state
from .storage import CandidateState, async_defer_candidate, async_set_candidate_state

STEP_CHOICE = vol.Schema(
    {
        vol.Required("decision", default="imported"): vol.In(
            {
                "imported": "Blueprint importiert / Automation erstellt",
                "defer": "Später nochmal erinnern",
                "dismiss": "Nicht mehr vorschlagen",
            }
        )
    }
)

STEP_DEFER = vol.Schema(
    {
        vol.Required("days", default=7): vol.All(int, vol.Range(min=1, max=365)),
    }
)

STEP_SEED_CHOICE = vol.Schema(
    {
        vol.Required("decision", default="done"): vol.In(
            {
                "done": "Ich habe daraus eine Automation erstellt",
                "defer": "Später nochmal erinnern",
                "dismiss": "Nicht mehr vorschlagen",
            }
        )
    }
)

STEP_DISABLE_INTEGRATION = vol.Schema(
    {
        vol.Required("confirm", default=False): bool,
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

            if user_input["decision"] == "defer":
                return await self.async_step_defer()

            await async_set_candidate_state(
                self.hass, self._entry_id, self._candidate_id, CandidateState.ACCEPTED
            )
            return self.async_create_entry(title="", data={"result": "accepted"})

        return self.async_show_form(step_id="init", data_schema=STEP_CHOICE)

    async def async_step_defer(self, user_input=None) -> data_entry_flow.FlowResult:
        if user_input is not None:
            from homeassistant.util import dt as dt_util

            days = int(user_input.get("days", 7))
            until = dt_util.utcnow().timestamp() + days * 86400
            await async_defer_candidate(
                self.hass,
                self._entry_id,
                self._candidate_id,
                until_ts=until,
            )
            return self.async_create_entry(title="", data={"result": "deferred", "days": days})

        return self.async_show_form(step_id="defer", data_schema=STEP_DEFER)


class SeedRepairFlow(RepairsFlow):
    def __init__(
        self,
        hass: HomeAssistant,
        *,
        entry_id: str,
        candidate_id: str,
        source: str,
        entities: str,
        excerpt: str,
    ) -> None:
        self.hass = hass
        self._entry_id = entry_id
        self._candidate_id = candidate_id
        self._source = source
        self._entities = entities
        self._excerpt = excerpt

    async def async_step_init(self, user_input=None) -> data_entry_flow.FlowResult:
        if user_input is not None:
            if user_input["decision"] == "dismiss":
                await async_set_candidate_state(
                    self.hass, self._entry_id, self._candidate_id, CandidateState.DISMISSED
                )
                return self.async_create_entry(title="", data={"result": "dismissed"})

            if user_input["decision"] == "defer":
                return await self.async_step_defer()

            await async_set_candidate_state(
                self.hass, self._entry_id, self._candidate_id, CandidateState.ACCEPTED
            )
            return self.async_create_entry(title="", data={"result": "accepted"})

        return self.async_show_form(
            step_id="init",
            data_schema=STEP_SEED_CHOICE,
            description_placeholders={
                "source": self._source,
                "entities": self._entities,
                "excerpt": self._excerpt,
            },
        )

    async def async_step_defer(self, user_input=None) -> data_entry_flow.FlowResult:
        if user_input is not None:
            from homeassistant.util import dt as dt_util

            days = int(user_input.get("days", 7))
            until = dt_util.utcnow().timestamp() + days * 86400
            await async_defer_candidate(
                self.hass,
                self._entry_id,
                self._candidate_id,
                until_ts=until,
            )
            return self.async_create_entry(title="", data={"result": "deferred", "days": days})

        return self.async_show_form(step_id="defer", data_schema=STEP_DEFER)


class DisableCustomIntegrationRepairFlow(RepairsFlow):
    def __init__(
        self,
        hass: HomeAssistant,
        *,
        issue_id: str,
        integration: str,
    ) -> None:
        self.hass = hass
        self._issue_id = issue_id
        self._integration = integration

    async def async_step_init(self, user_input=None) -> data_entry_flow.FlowResult:
        if user_input is not None:
            if not user_input.get("confirm"):
                return self.async_show_form(
                    step_id="init",
                    data_schema=STEP_DISABLE_INTEGRATION,
                    errors={"base": "confirm_required"},
                    description_placeholders={
                        "integration": self._integration,
                    },
                )

            tx = await async_disable_custom_integration_for_manifest_error(
                self.hass, integration=self._integration, issue_id=self._issue_id
            )
            return self.async_create_entry(title="", data={"result": "disabled", "tx": tx.data})

        return self.async_show_form(
            step_id="init",
            data_schema=STEP_DISABLE_INTEGRATION,
            description_placeholders={
                "integration": self._integration,
            },
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict | None,
) -> RepairsFlow:
    if not data:
        raise data_entry_flow.UnknownFlow

    # 1) Candidate suggestions
    entry_id = data.get("entry_id")
    candidate_id = data.get("candidate_id")
    if isinstance(entry_id, str) and isinstance(candidate_id, str):
        if data.get("kind") == "seed":
            source = str(data.get("seed_source") or "")
            entities = data.get("seed_entities")
            entities_str = ", ".join(entities) if isinstance(entities, list) else ""
            excerpt = str(data.get("seed_text") or "")
            # keep placeholders small
            excerpt = excerpt.strip().replace("\n", " ")
            if len(excerpt) > 160:
                excerpt = excerpt[:159] + "…"
            if len(entities_str) > 120:
                entities_str = entities_str[:119] + "…"
            return SeedRepairFlow(
                hass,
                entry_id=entry_id,
                candidate_id=candidate_id,
                source=source,
                entities=entities_str,
                excerpt=excerpt,
            )

        return CandidateRepairFlow(hass, entry_id=entry_id, candidate_id=candidate_id)

    # 2) Log findings
    finding_id = data.get("finding_id")
    if isinstance(finding_id, str) and issue_id.startswith("log_"):
        state = await async_get_log_fixer_state(hass)
        finding = (state.get("findings") or {}).get(finding_id)
        if isinstance(finding, dict) and finding.get("finding_type") == FindingType.MANIFEST_PARSE_ERROR:
            integration = (finding.get("details") or {}).get("integration")
            if isinstance(integration, str) and integration:
                return DisableCustomIntegrationRepairFlow(
                    hass,
                    issue_id=issue_id,
                    integration=integration,
                )

    raise data_entry_flow.UnknownFlow
