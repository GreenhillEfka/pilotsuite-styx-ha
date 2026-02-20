# Migration Guide - PilotSuite

## v0.12 → v0.13

### Breaking Changes

| Feature | Old | New | Migration |
|---------|-----|-----|-----------|
| Zone Storage | `habitus_zones_store.py` | `habitus_zones_store_v2.py` | Auto-migrated on first load |
| Entity Format | `list[]` | `tuple[]` | Auto-converted |

### Deprecated Features

| Feature | Deprecated | Removed |
|---------|------------|---------|
| v1 Zones | v0.12 | v0.14 |
| Old Forwarder | v0.11 | v0.14 |

### New Features

1. **Zone System v2** - 6 predefined zones
2. **Auto-Tag Integration** - Tags created automatically
3. **Inspector Sensors** - View internal state

---

## v0.11 → v0.12

### Breaking Changes

| Feature | Old | New |
|---------|-----|-----|
| Mood Weights | Dictionary | Character-based |

### Migration

```python
# Old
mood_weights = {"relaxed": 0.8, "focused": 0.5}

# New - use Character System
preset = "relaxed"  # weights auto-applied
```

---

## Upgrading

1. Backup current state:
   ```bash
   ha ai_copilot backup
   ```

2. Update integration:
   ```bash
   ha integrations update ai_home_copilot
   ```

3. Check migration status:
   ```bash
   ha ai_copilot status
   ```

---

## Rollback

If issues occur:
```bash
ha ai_copilot rollback
```
