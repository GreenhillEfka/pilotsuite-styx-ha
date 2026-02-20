# PilotSuite — Ethics & Governance

This project adds a *meaning layer* on top of Home Assistant to help users understand patterns, receive suggestions, and (optionally) execute actions.

The core idea: **better decisions require better context — but context must not become surveillance**.

## Non‑negotiables

> These are *defaults*, not dogma. If a maxim blocks a clearly better solution, we revisit it explicitly (issue + rationale + safeguards + doc update).

### 1) Privacy‑first
- **Local-first by default.** Any analysis should run locally. Remote calls are opt‑in.
- **Data minimization.** Only process what is required for the feature.
- **No personal defaults in the repo.** No IPs, entity IDs, tokens, names, or home-specific assumptions.
- **No secret leakage.** Tokens/keys must never be logged, exported into reports, or exposed as plain-text entities.

### 2) Governance‑first (consent)
- **No silent automation creation.** CoPilot may *suggest*, but the user confirms.
- **Actions are gated.** Risky actions must require explicit confirmation (Repairs flows, buttons, blueprints).
- **Autonomy is off by default.** Any self-acting mode must be a deliberate, reversible choice.
- **Rollback always.** Any “fix” must be reversible and logged.

### 3) Explainability over optimization
- Prefer: “*Here is why I think this is relevant*” over “*I optimized it*”.
- Suggestions should include the evidence and the reason, not only the conclusion.

### 4) Safety boundaries
- No medical/health claims. Mood is a **non-medical proxy**.
- No coercive behavior. No manipulation. No pressure.
- Quiet hours, guest mode, and presence sensitivity must be respected.

## Practical policy (how we implement it)

### Suggestions
- Suggestions are surfaced via **Repairs** (Issues) and/or notifications.
- The user accepts by running a blueprint, then confirming in Repairs.

### Fixes
- Fixes must be:
  - reversible (e.g., rename to disable)
  - rate-limited
  - logged (audit trail)

### Data handling
- Runtime settings live in **Config Entry options**.
- Derived state/caches live in **HA storage**.
- Secrets live in **Config Entry data** or Supervisor add-on options.

## Autonomy levels (proposal)
- **Level 0 (Default):** Observe + explain only.
- **Level 1:** Suggest (requires user confirmation).
- **Level 2:** Safe self-heal (bounded, reversible, audited).
- **Level 3:** Limited actions (only under policy engine + explicit opt-in).

## What we won’t build
- A system that tries to “optimize the human”.
- A system that quietly changes the home.
- A system that uploads raw logs/home timelines by default.
