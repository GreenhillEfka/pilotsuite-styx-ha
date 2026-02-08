# Dev Branch Policy (Home-Assistant-Copilot)

## Branches
- **`main`**: stabil / release-getrieben
  - Add-on Releases werden als Tags `copilot_core-vX.Y.Z` erstellt.

- **`dev`**: Work-in-progress
  - Hier landen Änderungen vor dem nächsten Add-on Release.
  - Ziel: immer buildbar, aber nicht zwingend "fertig".

## Wie du nachschaust
- GitHub → Branch `dev` → Commits/Diffs.

## Release-Flow
1) Merge `dev` → `main`
2) Tag `copilot_core-vX.Y.Z`
3) GitHub Release Notes

## Safety
- Keine Secrets im Repo.
- Privacy-first (Events/Logs/Diagnostics nur allowlisted + bounded).
