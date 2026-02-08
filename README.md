# Home Assistant CoPilot (MVP scaffold)

This repository is structured as a **Home Assistant Add-on repository** (for installing the Core service) and also contains a **custom integration scaffold** (adapter).

## Start here (docs index)
- **Start here:** `docs/START_HERE.md`
- **Ethics & Governance:** `docs/ETHICS_GOVERNANCE.md`
- **Changelog:** `CHANGELOG.md`

## Install (Add-on repo)
Home Assistant → Settings → Add-ons → Add-on Store → ⋮ → Repositories → add this repo URL.

Then install: **AI Home CoPilot Core (MVP)**.

## MVP endpoints
After install, open the add-on UI:
- `/health`
- `/version`

> This is a scaffold to validate the GitHub update/install pipeline. The neuron/mood/synapse engines and console UI come next.

## Channels
- Stable: GitHub Releases/Tags (recommended)
- Dev: opt-in branch builds

## Governance
No silent updates. Updates are explicit and should be logged as governance events in the CoPilot concept.
