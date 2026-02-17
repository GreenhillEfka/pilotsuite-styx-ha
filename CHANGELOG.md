# Changelog - PilotSuite Core Add-on

## [0.9.1-alpha.6] - 2026-02-17

### Added
- **MUPL Module:** Multi-User Preference Learning
  - UserRole: DEVICE_MANAGER, EVERYDAY_USER, RESTRICTED_USER, UNKNOWN
  - UserProfile: User profile with inferred role and preferences
  - RoleInferenceConfig: Konfiguration für role inference
  - MultiUserPreferenceLearning: Main engine für role inference und RBAC
  - create_mupl_module() factory function

### Features
- Device Manager Role: High device count + automation creation
- Everyday User Role: Regular device usage
- Restricted User Role: Limited device access
- Role-Based Access Control (RBAC): device access based on role
- Role inference from behavior patterns (device usage, automations)

### Tests
- Syntax-Check: ✅ mupl.py, __init__.py kompilieren
- MUPL Module: ✅ Created and exported

---

## [0.9.1-alpha.5] - 2026-02-17