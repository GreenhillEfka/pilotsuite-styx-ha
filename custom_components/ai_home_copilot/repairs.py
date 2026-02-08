from __future__ import annotations

import voluptuous as vol

from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
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
    def __init__(
        self,
        hass: HomeAssistant,
        *,
        entry_id: str,
        candidate_id: str,
        issue_id: str | None = None,
    ) -> None:
        self.hass = hass
        self._entry_id = entry_id
        self._candidate_id = candidate_id
        self._issue_id = issue_id

    async def _maybe_delete_issue(self) -> None:
        # Best-effort cleanup to avoid UI leftovers.
        if not self._issue_id:
            return
        try:
            ir.async_delete_issue(self.hass, DOMAIN, self._issue_id)
        except Exception:  # noqa: BLE001
            return

    async def async_step_init(self, user_input=None) -> data_entry_flow.FlowResult:
        if user_input is not None:
            if user_input["decision"] == "dismiss":
                await async_set_candidate_state(
                    self.hass, self._entry_id, self._candidate_id, CandidateState.DISMISSED
                )
                await self._maybe_delete_issue()
                return self.async_create_entry(title="", data={"result": "dismissed"})

            if user_input["decision"] == "defer":
                return await self.async_step_defer()

            await async_set_candidate_state(
                self.hass, self._entry_id, self._candidate_id, CandidateState.ACCEPTED
            )
            await self._maybe_delete_issue()
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
            return self.async_create_entry(
                title="", data={"result": "deferred", "days": days}
            )

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
        issue_id: str | None = None,
    ) -> None:
        self.hass = hass
        self._entry_id = entry_id
        self._candidate_id = candidate_id
        self._source = source
        self._entities = entities
        self._excerpt = excerpt
        self._issue_id = issue_id

    async def _maybe_delete_issue(self) -> None:
        if not self._issue_id:
            return
        try:
            ir.async_delete_issue(self.hass, DOMAIN, self._issue_id)
        except Exception:  # noqa: BLE001
            return

    async def async_step_init(self, user_input=None) -> data_entry_flow.FlowResult:
        if user_input is not None:
            if user_input["decision"] == "dismiss":
                await async_set_candidate_state(
                    self.hass, self._entry_id, self._candidate_id, CandidateState.DISMISSED
                )
                await self._maybe_delete_issue()
                return self.async_create_entry(title="", data={"result": "dismissed"})

            if user_input["decision"] == "defer":
                return await self.async_step_defer()

            await async_set_candidate_state(
                self.hass, self._entry_id, self._candidate_id, CandidateState.ACCEPTED
            )
            await self._maybe_delete_issue()
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
            return self.async_create_entry(
                title="", data={"result": "deferred", "days": days}
            )

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
        # Seed candidates
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
                issue_id=issue_id,
            )

        # Blueprint apply candidates (governance-first)
        if data.get("blueprint_id") or data.get("blueprint_path"):
            return RepairsBlueprintApplyFlow(
                hass,
                issue_id=issue_id,
                entry_id=entry_id,
                candidate_id=candidate_id,
                issue_data=data,
            )

        # Generic candidate (user does manual blueprint import)
        return CandidateRepairFlow(
            hass,
            entry_id=entry_id,
            candidate_id=candidate_id,
            issue_id=issue_id,
        )

    # 2) Log findings
    finding_id = data.get("finding_id")
    if isinstance(finding_id, str) and issue_id.startswith("log_"):
        state = await async_get_log_fixer_state(hass)
        finding = (state.get("findings") or {}).get(finding_id)
        if (
            isinstance(finding, dict)
            and finding.get("finding_type") == FindingType.MANIFEST_PARSE_ERROR
        ):
            integration = (finding.get("details") or {}).get("integration")
            if isinstance(integration, str) and integration:
                return DisableCustomIntegrationRepairFlow(
                    hass,
                    issue_id=issue_id,
                    integration=integration,
                )

    raise data_entry_flow.UnknownFlow


# --- Blueprint apply (governance-first) ---

STEP_BP_INIT = vol.Schema(
    {
        vol.Required("decision", default="preview"): vol.In(
            {
                "preview": "Vorschlag ansehen",
                "apply": "Automation jetzt erstellen (Blueprint anwenden)",
                "defer": "Später nochmal erinnern",
                "dismiss": "Nicht mehr vorschlagen",
            }
        )
    }
)

STEP_BP_CONFIGURE = vol.Schema(
    {
        vol.Required("a_entity"): str,
        vol.Optional("a_to_state", default="on"): str,
        vol.Required("b_target_entity_id"): str,
        vol.Optional("b_action", default="turn_on"): vol.In(["turn_on", "turn_off", "toggle"]),
    }
)

STEP_BP_CONFIRM = vol.Schema(
    {
        vol.Required("confirm", default=False): bool,
        vol.Optional("confirm_text", default=""): str,
    }
)


class RepairsBlueprintApplyFlow(RepairsFlow):
    def __init__(
        self,
        hass: HomeAssistant,
        *,
        issue_id: str,
        entry_id: str,
        candidate_id: str,
        issue_data: dict,
    ) -> None:
        self.hass = hass
        self._issue_id = issue_id
        self._entry_id = entry_id
        self._candidate_id = candidate_id
        self._issue_data = issue_data

        # Runtime state
        self._plan = None

    async def _maybe_delete_issue(self) -> None:
        try:
            ir.async_delete_issue(self.hass, DOMAIN, self._issue_id)
        except Exception:  # noqa: BLE001
            return

    def _risk(self) -> str:
        return str(self._issue_data.get("risk") or "medium")

    def _needs_configure(self, inputs: dict) -> bool:
        # For our shipped blueprint, we need at least a_entity + b_target.
        if not isinstance(inputs, dict):
            return True
        if not inputs.get("a_entity"):
            return True
        if not inputs.get("b_target"):
            return True
        return False

    async def async_step_init(self, user_input=None) -> data_entry_flow.FlowResult:
        if user_input is not None:
            decision = user_input.get("decision")

            if decision == "dismiss":
                await async_set_candidate_state(
                    self.hass, self._entry_id, self._candidate_id, CandidateState.DISMISSED
                )
                await self._maybe_delete_issue()
                return self.async_create_entry(title="", data={"result": "dismissed"})

            if decision == "defer":
                return await self.async_step_defer()

            if decision == "apply":
                # Build plan from issue data.
                from .repairs_blueprints import async_build_plan_from_issue_data

                self._plan = async_build_plan_from_issue_data(
                    entry_id=self._entry_id,
                    candidate_id=self._candidate_id,
                    issue_id=self._issue_id,
                    data=self._issue_data,
                )

                # Ensure inputs exist (v0.1: allow user to enter minimal required).
                inputs = dict(getattr(self._plan, "blueprint_inputs", {}) or {})
                if self._needs_configure(inputs):
                    return await self.async_step_configure()

                return await self.async_step_confirm()

            # preview
            return self.async_show_form(
                step_id="init",
                data_schema=STEP_BP_INIT,
                description_placeholders={
                    "blueprint": str(self._issue_data.get("blueprint_id") or "ai_home_copilot/a_to_b_safe.yaml"),
                    "risk": self._risk(),
                },
            )

        return self.async_show_form(
            step_id="init",
            data_schema=STEP_BP_INIT,
            description_placeholders={
                "blueprint": str(self._issue_data.get("blueprint_id") or "ai_home_copilot/a_to_b_safe.yaml"),
                "risk": self._risk(),
            },
        )

    async def async_step_configure(self, user_input=None) -> data_entry_flow.FlowResult:
        if user_input is not None:
            # Validate entities exist (best-effort).
            a_entity = str(user_input.get("a_entity") or "").strip()
            b_entity = str(user_input.get("b_target_entity_id") or "").strip()
            if not a_entity or not b_entity:
                return self.async_show_form(
                    step_id="configure",
                    data_schema=STEP_BP_CONFIGURE,
                    errors={"base": "invalid"},
                )
            if self.hass.states.get(a_entity) is None or self.hass.states.get(b_entity) is None:
                return self.async_show_form(
                    step_id="configure",
                    data_schema=STEP_BP_CONFIGURE,
                    errors={"base": "invalid"},
                )

            # Map to blueprint inputs.
            inputs = {
                "a_entity": a_entity,
                "a_to_state": str(user_input.get("a_to_state") or "on"),
                "a_for": {"seconds": 0},
                "conditions": [],
                "b_target": {"entity_id": b_entity},
                "b_action": str(user_input.get("b_action") or "turn_on"),
            }

            if self._plan is None:
                from .repairs_blueprints import async_build_plan_from_issue_data

                self._plan = async_build_plan_from_issue_data(
                    entry_id=self._entry_id,
                    candidate_id=self._candidate_id,
                    issue_id=self._issue_id,
                    data=self._issue_data,
                )

            # Freeze updated inputs.
            self._plan = type(self._plan)(
                **{
                    **self._plan.__dict__,
                    "blueprint_inputs": inputs,
                }
            )

            return await self.async_step_confirm()

        return self.async_show_form(step_id="configure", data_schema=STEP_BP_CONFIGURE)

    async def async_step_confirm(self, user_input=None) -> data_entry_flow.FlowResult:
        if user_input is not None:
            if not user_input.get("confirm"):
                return self.async_show_form(
                    step_id="confirm",
                    data_schema=STEP_BP_CONFIRM,
                    errors={"base": "confirm_required"},
                )

            if self._risk() == "high":
                txt = str(user_input.get("confirm_text") or "").strip()
                if txt != "CONFIRM":
                    return self.async_show_form(
                        step_id="confirm",
                        data_schema=STEP_BP_CONFIRM,
                        errors={"base": "confirm_required"},
                    )

            # Apply.
            from .repairs_blueprints import async_apply_plan

            if self._plan is None:
                raise data_entry_flow.UnknownFlow

            await async_apply_plan(self.hass, self._plan)

            await async_set_candidate_state(
                self.hass, self._entry_id, self._candidate_id, CandidateState.ACCEPTED
            )
            await self._maybe_delete_issue()

            return self.async_create_entry(title="", data={"result": "applied"})

        return self.async_show_form(
            step_id="confirm",
            data_schema=STEP_BP_CONFIRM,
            description_placeholders={
                "risk": self._risk(),
                "note": "Bei risk=high musst du zusätzlich CONFIRM eintippen.",
            },
        )

    async def async_step_defer(self, user_input=None) -> data_entry_flow.FlowResult:
        # Reuse the generic defer UI.
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
