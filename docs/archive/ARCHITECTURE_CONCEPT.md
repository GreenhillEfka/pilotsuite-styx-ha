# Architektur-Konzept: Eine oder Zwei Projekte?

## Aktuelle Situation

| Projekt | Version | Verantwortung |
|---------|---------|---------------|
| HA Integration | v0.12.1 | Frontend, Entities, Dashboard Cards |
| Core Add-on | v0.7.0 | Backend, API, Brain Graph, Logik |

---

## Option A: Zwei Projekte (aktuell)

### ✅ Vorteile
1. **Klare Trennung** - HA-Integration ↔ Backend-Logik
2. **Unabhängige Releases** - können separat deployed werden
3. **Kleinere Deployments** - User braucht nur, was er braucht
4. **HA-Ökosystem** - offizielles HACS-Repo für Integration

### ❌ Nachteile
1. **Synchronisierungsaufwand** - Versionen müssen zusammenpassen
2. **Doppelte Entwicklung** - 2x Repo, 2x CI/CD, 2x Tests
3. **Komplexität** - 2 Repos für ein Feature

---

## Option B: Ein Projekt

### ✅ Vorteile
1. **Einheitliche Entwicklung** - ein Repo für alles
2. **Einfachere Releases** - eine Version für alles
3. **Keine Sync-Probleme** - keine Version-Mismatches

### ❌ Nachteile
1. **Größeres Deployment** - User müssen alles installieren
2. **HACS-Limit** -HA-Integration muss HACS-konform bleiben
3. **Komplexeres Backend** - Core-Logik in HA-Repo

---

## Empfehlung: Zwei Projekte (beibehalten)

### Begründung:

1. **HACS-Integration erfordert Separation**
   - HA-Integration muss offizielles HACS-Repo sein
   - Core Add-on ist separates Add-on

2. **Unabhängige Skalierung**
   - Backend kann unabhängig vom Frontend entwickelt werden
   - Verschiedene Teams können parallel arbeiten

3. **Flexibilität**
   - User können nur Frontend oder nur Backend nutzen
   - Headless-Betrieb möglich

4. **Bekanntes Muster**
   - Viele HA-Add-ons nutzen dieses Pattern
   - z.B. ESPHome, Node-RED

---

## Hybrid-Lösung: Gemeinsame Dokumentation

| Ebene | Projekt | Beschreibung |
|-------|---------|-------------|
| **Vision** | PilotSuite Docs | Überblick, Roadmap |
| **Frontend** | HA Integration | Entities, Cards, UI |
| **Backend** | Core Add-on | API, Brain Graph |

---

## Fazit

**Zwei Projekte beibehalten!** 

Grund: HACS-Anforderungen, unabhängige Entwicklung, Flexibilität.

**Aber:** Bessere Synchronisierung via:
- Gemeinsame CHANGELOG
- Gekoppelte Versionierung (v0.12.x = HA + Core)
- Einheitliche CI/CD Pipeline
