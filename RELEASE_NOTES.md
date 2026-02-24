# Release Notes v7.9.3 (2026-02-24)

- fix(anomaly_detector): ensure is_anomaly returns Python bool type (fixes np.False_ isinstance check)
- fix(anomaly_detector): correct last_anomaly timestamp and features to reflect last true anomaly
- fix(manifest): bump ai_home_copilot to v7.9.3 and root manifest to v7.9.3
- tests: all 608 tests passing

---

# Release Notes v7.9.1 (2026-02-24)

- Fixed anomaly detector tests: correct last anomaly calculation and bool type consistency.
- Extended habit predictor with scene grouping in routine extraction.
- Synced with core v7.9.0.
- Test tag: test-p0-202602240915
- Feature tag: v7.9.1
