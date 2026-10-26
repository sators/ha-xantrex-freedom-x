# Changelog

## 0.2.0

- Distinguish AC input from output using controlled bypass/inverter/bypass captures. Expose both voltage/frequency pairs and an explicitly inferred power path; ambiguous states remain unknown.
- Add real LOAD watts and reported load percentage. Correct earlier provisional mappings: byte 8 is apparent power in VA, byte 10 is real power in W, not current. New entities avoid mixing incompatible old history.
- Keep reported battery percentage provisional until validated below 100%; no inverter DC current or raw mode flag is claimed.
- Add an on-demand, serialized diagnostic capture of additional custom-service blocks. Routine polling still reads only the original telemetry blocks; no writes are implemented.
- Avoid duplicate Bluetooth discovery for an already configured address. Existing disabled channel-2 entities may need manual enabling after upgrade.

## 0.1.2

- Show battery voltage and provisional AC current with two decimal places, and AC voltage/frequency with one. Home Assistant's whole-number default hid useful precision (for example, 14.52 V appeared as 15 V).
- Verified HACS release installation, device identity, live raw telemetry, and repeated polling on one Freedom X 2000 12 V setup. Additional models and operating modes remain unverified.

## 0.1.1

- Use the exact Bluetooth service UUID for discovery. The earlier `ID*` local-name pattern was rejected by Home Assistant's Bluetooth matcher and could prevent Bluetooth from starting. Existing 0.1.0 installations should redownload through HACS and restart Home Assistant Core.
- Test the manifest against Home Assistant's real Bluetooth matcher during CI.
- Document HACS custom-repository installation, setup, updates, removal, troubleshooting, and compatibility reporting.

## 0.1.0

- Initial experimental, read-only Freedom X 2000 12 V Bluetooth protocol prototype.
- AC voltage, frequency, battery voltage, telemetry availability, optional provisional fields, and redacted diagnostics.
