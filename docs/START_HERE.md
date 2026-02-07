# Start here — AI Home CoPilot (HA Integration)

This is the Home Assistant **custom integration** (`ai_home_copilot`).

## What this project is
A privacy-first, governance-first layer that helps you:
- observe patterns,
- surface *explainable* suggestions,
- apply changes only with explicit confirmation (Repairs + Blueprints),
- keep fixes reversible and auditable.

## Quick links
- Project plan / Kanban: [`PROJECT_PLAN.md`](./PROJECT_PLAN.md)
- Operations (reload vs restart): [`OPERATIONS.md`](./OPERATIONS.md)
- Dashboard template: [`DASHBOARD_LOVELACE.md`](./DASHBOARD_LOVELACE.md)
- Dev surface (observability): [`DEV_SURFACE.md`](./DEV_SURFACE.md)
- DevLogs pipeline (debug): [`DEVLOGS.md`](./DEVLOGS.md)
- Security & Privacy: [`SECURITY_PRIVACY.md`](./SECURITY_PRIVACY.md)
- Ethics & Governance: [`ETHICS_GOVERNANCE.md`](./ETHICS_GOVERNANCE.md)
- Release checklist: [`RELEASE_CHECKLIST.md`](./RELEASE_CHECKLIST.md)

## How to contribute (rules of the road)
- No personal defaults (IPs, entity_ids, names).
- No secrets in code/logs/docs.
- No silent automations or risky actions without explicit confirmation.
- Prefer reload-first changes.

If any of the above principles blocks a clearly better solution, we **revisit it explicitly** (open an issue, document the rationale, update the policy docs).
