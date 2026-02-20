# Branch & Tag Cleanup

Alle Feature-Branches sind in `main` konsolidiert (v3.9.1). Diese Anleitung dokumentiert was geloescht werden kann.

## HACS Integration (pilotsuite-styx-ha)

### Branches loeschen (alle obsolet — Code auf main)

```bash
# Obsolete Feature-Branches
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-ha/git/refs/heads/development
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-ha/git/refs/heads/dev-habitus-dashboard-cards
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-ha/git/refs/heads/dev/autopilot-2026-02-15
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-ha/git/refs/heads/dev/mupl-phase2-v0.8.1
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-ha/git/refs/heads/dev/openapi-spec-v0.8.2
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-ha/git/refs/heads/dev/vector-store-v0.8.3
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-ha/git/refs/heads/dev/tag-registry-v0.1
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-ha/git/refs/heads/wip/phase4-ml-patterns
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-ha/git/refs/heads/wip/module-forwarder_quality/20260208-172947
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-ha/git/refs/heads/wip/module-unifi_module/20260209-2149
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-ha/git/refs/heads/wip/module-unifi_module/20260215-0135
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-ha/git/refs/heads/backup/pre-merge-20260216
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-ha/git/refs/heads/backup/2026-02-19

# Merged Work-Branches
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-ha/git/refs/heads/claude/research-repos-scope-4e3L6
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-ha/git/refs/heads/claude/consolidate-repos-overview-bnGGO
```

### Garbage Tags loeschen

```bash
git push origin --delete vv0.8.0
git push origin --delete v--dry-run
```

### Verbleibende Branches

- `main` — Production (v3.9.1)
- `development` — (neu erstellen von main)

---

## Core Add-on (pilotsuite-styx-core)

### Branches loeschen (alle obsolet — Code auf main)

```bash
# Legacy master (alte Autopilot-History, keine shared history mit main)
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-core/git/refs/heads/master

# Obsolete Feature-Branches
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-core/git/refs/heads/dev
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-core/git/refs/heads/dev-habitus-dashboard-cards
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-core/git/refs/heads/wip/phase5-collective-intelligence
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-core/git/refs/heads/wip/phase5-cross-home
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-core/git/refs/heads/release/v0.4.1
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-core/git/refs/heads/backup/pre-merge-20260216
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-core/git/refs/heads/backup/2026-02-19

# Merged Work-Branches
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-core/git/refs/heads/claude/research-repos-scope-4e3L6
gh api -X DELETE repos/GreenhillEfka/pilotsuite-styx-core/git/refs/heads/claude/consolidate-repos-overview-bnGGO
```

### Garbage Tags loeschen

```bash
git push origin --delete vv0.8.0
```

### Verbleibende Branches

- `main` — Production (v3.9.1)
- `development` — (neu erstellen von main)

---

## Zusammenfassung

| Repo | Vorher | Nachher |
|------|--------|---------|
| HACS | 15 Branches | 2 (main + development) |
| Core | 11 Branches | 2 (main + development) |
| Tags bereinigt | vv0.8.0, v--dry-run | Entfernt |

Alle einzigartigen Features wurden geprueft — nichts geht verloren:
- wip/phase5-cross-home: READMEs extrahiert (SDKs, Sharing, Swagger)
- Alle anderen: Code ist identisch oder superseded auf main
