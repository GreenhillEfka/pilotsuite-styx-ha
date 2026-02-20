# Dev Branch Policy (pilotsuite-styx-ha)

Ziel: Du sollst jederzeit sehen können, woran gerade gearbeitet wird – **ohne** dass Releases/Tags dauernd erzeugt werden.

## Branches
- **`main`**: stabil / release-getrieben
  - Releases entstehen als Tags `vX.Y.Z`.
  - Das ist der Branch, den HACS typischerweise über Releases installiert.

- **`development`**: „Work in progress“ (WIP)
  - Hier landen Änderungen **vor** dem nächsten Release.
  - Kann vorübergehend unfertig sein (aber soll immer buildbar bleiben).
  - Keine Garantie, dass jede Commit-Serie schon eine saubere Migration hat.

## Wie du nachschaust
- GitHub → Branch `development` öffnen → Commits/Diffs ansehen.

## Wie wir releasen
- Wenn ein Feature fertig + getestet ist:
  1) Merge `development` → `main`
  2) Tag `vX.Y.Z`
  3) GitHub Release Notes

## Sicherheit/Privacy
- Keine Secrets/Tokens im Repo.
- Learned/Candidate Aktionen bleiben governance-first (Repairs/Blueprint bestätigen).
