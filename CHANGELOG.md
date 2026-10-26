# Changelog

## 0.1.1

- Use the exact Bluetooth service UUID for discovery. The earlier `ID*` local-name pattern was rejected by Home Assistant's Bluetooth matcher and could prevent Bluetooth from starting. Existing 0.1.0 installations should redownload through HACS and restart Home Assistant Core.
- Test the manifest against Home Assistant's real Bluetooth matcher during CI.
- Document HACS custom-repository installation, setup, updates, removal, troubleshooting, and compatibility reporting.

## 0.1.0

- Initial experimental, read-only Freedom X 2000 12 V Bluetooth protocol prototype.
- AC voltage, frequency, battery voltage, telemetry availability, optional provisional fields, and redacted diagnostics.
