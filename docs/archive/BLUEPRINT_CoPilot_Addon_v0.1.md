# AI Home CoPilot – Blueprint v0.1 (Home Assistant Add-on + Custom Panel)

Status: Entwurf für MVP-Umsetzung. **Keine Technikdetails/YAML**, aber implementierungsnah.

## 0) Zielbild (ein Satz)
**Erklärendes, begrenztes, dialogisches Entscheidungssystem**: bewertet (Neuronen), bündelt Bedeutung (Moods), berechnet Relevanz (Synapsen), erzeugt Vorschläge, erhält Freigaben, lässt Home Assistant ausführen – **ohne Autopilot/Agent/Blackbox**.

Normative Kette (nicht verletzbar):
`States → Neuronen → Moods → Synapsen → Vorschläge → Dialog/Freigabe → HA-Aktion`

## 1) MVP-Use-Cases (Pilot)
Räume/Scopes:
- Bad (morgens)
- Wohnzimmer (morgens: Wetter + Musik)
- Wohnzimmer (abends)
- Schlafenszeit (quer; Aktionen zunächst nur Bad/Wohnzimmer)

Aktionsdomänen (Assisted, nur nach Bestätigung):
- Licht (Bad/Wohnzimmer)
- Musik/Media (Wohnzimmer)
- **Message-DND (HA-notify dämpfen)** (HA-eigene Benachrichtigungen; iOS/OS-DND später)

Plattform/UX:
- iOS zuerst, primärer Kanal: **Home Assistant App Push**
- **Kritisch = HA Persistent Notifications** (Gefahr + Governance-kritisch)
- Rest: **Inbox im CoPilot Panel** („x neue Vorschläge“), optional sparsame Pushes für Assisted-Entscheidungen

## 2) Komponenten (Architektur)
### 2.1 CoPilot Core Service (plattformneutral)
Läuft als Webservice mit stabiler API (LAN erreichbar):
- Neuron Engine (deterministisch, stateless; Zeit nur Glättung)
- Mood Engine (Aggregation; nicht exklusiv; inkl. conflict/uncertainty)
- Synapsen/Relevanz Engine (Mood→Option-Relevanz; negative Synapsen möglich)
- Policy Engine (Manual/Assisted/Auto; Scope-basiert; Timeout/Exit zwingend)
- Decision Bundle Builder (strukturierte Pros/Cons/Warum-Kette; LLM-freundlich)
- Logging/Audit Store (append-only, rekonstruierbar)
- RAG/Inference optional (nur für Erklärung/Consistency-Checks, nie exekutiv)

### 2.2 Home Assistant Integration (Adapter + Execution)
- Ingest: HA States/Areas/History-Slices → Core
- Execute: Core Option/Action → HA Services/Scripts
- Expose: Entities/Services für Inbox, Policies, Status, Debug
- Push: iOS actionable notifications (JA/NEIN/SPÄTER/DETAILS)

### 2.3 CoPilot Console UI (Custom Panel / Sidepanel)
„Entwicklungsumgebung“ in HA:
- Inbox
- Now
- History/Audit
- Modules & Weights (versioniert/undo)
- Brain (read-only)
- Chat/Dev Console

## 3) Datenmodell (minimal, auditfähig)
Kanonische Objekte (Core):
- NeuronScore {t, scope, neuron_id, value, inputs_used, smoothing_meta}
- MoodSnapshot {t, scope, mood_vector, contributors, uncertainty, conflict}
- Option {option_id, domain, description}
- Synapse {synapse_id, source_moods, target_option, weight, threshold, direction, enabled, version}
- Suggestion {id, t, scope, option_id, relevance, pros, cons, required_policy, requires_confirmation}
- Policy {id, actor, scope, mode, condition, duration/exit, constraints}
- LogEvent (append-only) {t, type, source, context, explanation_bundle, links}

LogEvent-Typen (Kap. 9):
- observation.* (Neuron/Mood Änderungen)
- decision.suggestion / decision.prioritization
- action.executed / action.failed / action.rolled_back
- governance.mode_change / governance.policy_change / governance.update
- learning.* (nur in Lernphase)

## 4) Policies / Modi (MVP)
Global: **Manual**.
Assisted (opt-in) nur für:
- Bad/Wohnzimmer Licht
- Wohnzimmer Media
- Message-DND

Zwingend:
- Jede Assisted/Auto-Policy hat **Exit-Kriterium** + **globales Timeout**
- Unsicherheit/Conflict reduziert Handlungsspielraum (mindestens blockiert autonomes Handeln)
- Explizite Nutzeraktion schlägt Autonomie (temporäre Suspendierung + Marker)

Kritisch (Persistent Notifications):
- echte Gefahren (später)
- **Governance-kritisch**: Autonomie/Assisted aktiv/ablaufend, Policy-Verletzung, Update gestartet/fehlgeschlagen, Rollback notwendig

## 5) Chat/Benachrichtigungs-Flows (iOS + Panel)
### 5.1 Assisted Push (iOS Actions)
- Nachricht: Vorschlag + Kurzbegründung
- Actions: JA / NEIN / SPÄTER / DETAILS
- JA erzeugt: decision.user_accept → action.execute (HA) → action.executed → ggf. rollback marker

### 5.2 Inbox im Panel
- „x neue Vorschläge“ + Liste (Titel, Raum, Relevanz, Kurz-Warum)
- Pro Vorschlag: Ausführen/Ablehnen/Später/Warum?

### 5.3 Governance Persistent Notifications
- Nicht dämpfbar im MVP
- Erfordern Quittierung (ack)

## 6) Brain Visualization (read-only)
Layer strikt:
- Neuronen (Detail)
- Moods (Sinn)
- Synapsen (Relevanz)
- Vorschläge (Handlungsraum ohne Handlung)
- Meta (Stabilität/Unsicherheit/Lernphase)

Zeitachsen:
- Now
- Kurzzeit (Min/Std)
- Langzeit (Tage/Wochen; später)

Interaktion erlaubt: Hover/Fokus, Pfade highlighten, Zeit-Rückblick.
Verboten: Gewicht direkt ändern, Synapsen togglen, Aktionen auslösen.

## 7) RAG + Rückschluss (optional, aber vorbereitet)
**RAG**: Dossier + Policies + Change-Log + relevante Log-Ausschnitte.
**Inference/Guard**: prüft Konsistenz (Policy/Mode/Belege) bevor LLM formuliert.
LLM Rollen:
- Explainer (nur aus Explanation Bundle)
- Question Generator (Konflikte/Unsicherheit)
- Formatter

## 8) GitHub Update-Mechanismus (Stable + Dev) – Governance-konform
Ziel: schnelle Updates in HA, aber auditierbar + rollback.

### 8.1 Kanäle
- **Stable**: GitHub Releases/Tags (Default)
- **Dev**: opt-in (Branch/Nightly), nur für Tests

### 8.2 Regeln (hart)
- Kein stilles Update (kein „git pull bei Start“)
- Update ist Governance-Event: `governance.update` + Persistent Notification
- Jede Version hat: Version-ID, Changelog, Migrationshinweis (falls nötig)
- Rollback möglich (zur vorherigen Version)

## 9) Repository-Struktur (empfohlen)
Wir trennen Deploy-/HA-spezifisches von Core, aber im selben Repo möglich:

- `/repository.json`  (Add-on Repo Manifest für HA Add-on Store)
- `/addons/copilot_core/`  (Add-on: Core Service + optional UI)
- `/custom_components/copilot/`  (HA Integration: Entities/Services/Push Actions/Panel wiring)
- `/docs/`  (Dossier, Konzepte, Changelogs)

Hinweis: Erst wenn `repository.json` + Add-on Ordner existieren, ist die Repo-URL in HA als Add-on Repository sinnvoll.

## 10) MVP Deliverables (Checkliste)
1) Core API: ingest/query/confirm/audit/policy/update-status
2) Neuron/Mood/Synapse minimal set (Bad/WZ/Schlaf)
3) Inbox + Suggestion lifecycle (new/read/defer/accept/reject)
4) iOS actionable notifications + event handling
5) Append-only Audit Log + Rekonstruktion „warum letzte Woche anders?“
6) Console Panel: Inbox/Now/History/Modules/Brain/Chat
7) Update Governance: Stable/Dev + Marker + Rollback-Plan

---

## Offene Entscheidungen (kurz)
- Welche Notifications-Klassen gelten als „Info“ vs. „Warnung“ vs. „Kritisch“ (für Message-DND Gate)?
- Start ohne „social“ Mood (empfohlen) oder minimal aktiv?
- Soll „TV pause“ im MVP nur vorgeschlagen werden (empfohlen) oder Assisted ausführbar?
