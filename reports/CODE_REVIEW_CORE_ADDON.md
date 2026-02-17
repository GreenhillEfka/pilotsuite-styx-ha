**Summary**
- P0: 0
- P1: 2
- P2: 4
- P3: 2
- Tests: nicht ausgefuehrt (Review-only)

**Findings**
- P1: Authentifizierung ist inkonsistent und haengt vom Entry-Point ab; im `create_app`-Pfad ist Auth nur aktiv, wenn ein Token gesetzt ist, und mehrere `api_v1`-Endpoints haben keinen eigenen Auth-Check. Evidence: `addons/copilot_core/rootfs/usr/src/app/copilot_core/app.py:270`, `addons/copilot_core/rootfs/usr/src/app/copilot_core/api/v1/graph_ops.py:75`, `addons/copilot_core/rootfs/usr/src/app/copilot_core/api/v1/search.py:436`, `addons/copilot_core/rootfs/usr/src/app/copilot_core/api/v1/notifications.py:435`, `addons/copilot_core/rootfs/usr/src/app/copilot_core/api/v1/voice_context_bp.py:9`, `addons/copilot_core/rootfs/usr/src/app/copilot_core/api/v1/dashboard.py:26`. Empfehlung: Auth zentral erzwingen (globales `before_request` mit `validate_token` + Allowlist fuer Health/Version), `auth_required` konsistent aus Optionen lesen und alle Schreib-Endpoints explizit schuetzen.
- P1: UniFi Auth ist praktisch wirkungslos, weil der Client den erwarteten Key per Header mitliefert. Evidence: `addons/copilot_core/rootfs/usr/src/app/copilot_core/unifi/api.py:18`. Empfehlung: `require_api_key` aus `copilot_core.api.security` verwenden oder den erwarteten Key nur aus Config/Env laden; niemals aus Request.
- P2: Produktions-Entry (Docker) nutzt `main.py`, Tests laufen aber ueber `create_app`; dadurch sind Blueprint-Registrierung und Auth-Logik divergierend und Teile der API evtl. ungetestet oder nicht erreichbar. Evidence: `addons/copilot_core/Dockerfile:20`, `addons/copilot_core/rootfs/usr/src/app/main.py:44`, `addons/copilot_core/rootfs/usr/src/app/copilot_core/core_setup.py:150`, `addons/copilot_core/rootfs/usr/src/app/tests/test_vector_endpoints.py:6`. Empfehlung: einen einheitlichen App-Factory-Pfad etablieren und sowohl `main.py` als auch Tests darauf basieren.
- P2: Rate Limiting ist implementiert, wird aber in keinem Endpoint angewandt; zudem fehlen globale Request-Size-Limits. Evidence: `addons/copilot_core/rootfs/usr/src/app/copilot_core/api/rate_limit.py:132`. Empfehlung: `@rate_limit` auf ingest/search/notifications/vector anwenden und `MAX_CONTENT_LENGTH` setzen.
- P2: Vector API erzeugt pro Request neue Event-Loops und hat ein Error-Handling-Loch (loop kann bei ValueError nicht existieren). Evidence: `addons/copilot_core/rootfs/usr/src/app/copilot_core/api/v1/vector.py:173`. Empfehlung: `loop = None` + konditionales Close oder `asyncio.run` verwenden; alternativ Store-Methoden sync machen.
- P2: CandidateStore schreibt JSON ohne Synchronisierung; parallele Requests koennen Daten verlieren oder die Datei korrupt schreiben. Evidence: `addons/copilot_core/rootfs/usr/src/app/copilot_core/candidates/store.py:98`. Empfehlung: Thread-Lock um Mutationen/IO oder Migration auf SQLite.
- P3: Fehlerantworten enthalten rohe Exception-Texte. Evidence: `addons/copilot_core/rootfs/usr/src/app/copilot_core/api/v1/notifications.py:494`, `addons/copilot_core/rootfs/usr/src/app/copilot_core/api/v1/vector.py:55`, `addons/copilot_core/rootfs/usr/src/app/copilot_core/api/v1/dashboard.py:110`. Empfehlung: generische Fehlermeldungen im Response, Details nur im Log.
- P3: `is_auth_required` behauptet Options-Support, liest ihn aber nicht. Evidence: `addons/copilot_core/rootfs/usr/src/app/copilot_core/api/security.py:29`. Empfehlung: Options-Read implementieren oder Doku anpassen.

**Security Checklist (Requested)**
- SQL Injection: keine direkten Findings; SQL-Statements nutzen Parameterbindung. Evidence: `addons/copilot_core/rootfs/usr/src/app/copilot_core/brain_graph/store.py:93`, `addons/copilot_core/rootfs/usr/src/app/copilot_core/vector_store/store.py:150`.
- XSS: keine direkten Findings; DOT/SVG-Labels werden escaped. Evidence: `addons/copilot_core/rootfs/usr/src/app/copilot_core/brain_graph/render.py:120`.
- Secrets: keine hardcodierten Secrets gefunden; Dev-Logs werden best-effort sanitisiert. Evidence: `addons/copilot_core/rootfs/usr/src/app/copilot_core/api/v1/dev.py:46`.

**Performance Notes**
- BrainGraphStore oeffnet pro Operation neue SQLite-Verbindungen, obwohl ein Pool existiert. Evidence: `addons/copilot_core/rootfs/usr/src/app/copilot_core/brain_graph/store.py:93`, `addons/copilot_core/rootfs/usr/src/app/copilot_core/performance.py:329`. Empfehlung: Pool nutzen oder eine geteilte Connection mit Lock einsetzen.
