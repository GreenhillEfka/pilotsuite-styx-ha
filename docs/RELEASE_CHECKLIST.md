# Release checklist

Goal: keep releases stable, reversible, and well-documented.

## Before tagging
- [ ] Update `CHANGELOG.md` (move items from Unreleased into a version section).
- [ ] Verify manifest version matches the tag.
- [ ] Confirm privacy/governance rules still hold (no secrets, no silent automations).
- [ ] Smoke test:
  - [ ] Integration loads
  - [ ] Online/version entities update
  - [ ] Webhook still works
  - [ ] Buttons work (no exceptions)

## Release notes
- [ ] Summarize user-facing changes.
- [ ] Mention any required HA restart.
- [ ] Mention migrations, if any.

### Release notes snippet (copy/paste)

```text
Summary:
- 

User-visible changes:
- 

Ops / Upgrade notes:
- HACS update requires HA restart.
- If Options changed: reload entry via button.ai_home_copilot_reload_config_entry.

Privacy/Governance:
- 

Known issues:
- 
```

## After tagging
- [ ] Create GitHub Release with notes.
- [ ] Optional: add a short “upgrade notes” section in README.
