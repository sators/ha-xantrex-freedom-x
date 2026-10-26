# Comparing a Freedom X remote with FXC Control

The integration is read-only. These comparisons validate interpretation of telemetry; they do not validate inverter protection or control functions. Use normal RV power controls only when an interruption is acceptable. Do not change low-voltage cutoffs, output limits, transfer settings, or other protective settings to obtain a sample.

## Capture a matched observation

1. Keep a steady, modest load and record the physical panel's mode.
2. Temporarily disable the integration entry so FXC Control can connect. Record the Status screen's input voltage/current/frequency, LOAD voltage/watts/percentage, battery voltage/current/percentage, and time.
3. Disconnect FXC Control and any scanner app, then enable the integration again. Wait for telemetry availability to become connected.
4. Choose **Download diagnostics**. A successful `protocol_capture` contains its own UTC observation time, the two telemetry frames, and additional custom-service fields. Check this timestamp rather than assuming the last periodic sample is new. A capture with `error_type` is not usable evidence for the new operating state.
5. Record the time difference and whether loads changed. Bluetooth connection sharing means app and HA observations are normally sequential, not simultaneous. Allow for rounding and changing loads; never force a dynamic reading to fit a proposed mapping.
6. Repeat the baseline after each change. A bypass → inverter → bypass sequence helps separate mode-related changes from load or battery-voltage changes.

Keep full diagnostics private until reviewed. The integration excludes its known address/serial fields, but Home Assistant's export wrapper can contain installation metadata and unmapped blocks may contain information whose meaning is not yet known. Share only reviewed, relevant bytes. Replace real identifiers in public fixtures.

## Useful comparisons

| Comparison | What it can establish | Current evidence |
| --- | --- | --- |
| Bypass → DC inverter → bypass, steady load | Input/output pair direction and candidate mode bits | Input falls to zero while output stays 120 V / 60 Hz, then input/output match again |
| Two ordinary load levels in each mode | Real watts, apparent VA, reported percentage | Real watts closely match the app; more matched load points welcome |
| Battery percentage below 100% | Whether the candidate percentage follows FXC Control | Pending; full-scale 100% alone is insufficient |
| Different naturally occurring battery voltages | DC voltage scaling | 13.59–14.52 V captured; app comparison consistent |
| Output off, when normally appropriate | Off/standby states and mode bits | Not yet captured; no-output inference is tested with synthetic frames only |
| Naturally occurring warning/fault, without provoking one | Warning/fault bit meanings | Unmapped; do not induce faults for testing |
| Settings screen readback with unchanged settings | Candidate configuration field scales | Unmapped; matching one value is insufficient to expose controls |

## Separate measurements from interpretations

- Byte offsets 0/2 and 4/6 in `1910/2A03` are input and output V/Hz pairs.
- Offset 8 is apparent VA; offset 10 is real LOAD W. They are different physical quantities. A current estimate from VA/V would be derived, not a measured current field.
- Offset 12 is the reported load percentage. Do not assume `W / 2000` equals the panel's percentage.
- Offset 16 is DC voltage. It does not establish DC current or battery state of charge.
- `1910/2A04` offset 0 remains a candidate battery percentage until compared below full charge.
- The current power-path entity is explicitly inferred from input/output V/Hz, not a confirmed raw mode flag. Its `basis` attribute records that distinction.
- BMS/shunt signed current and power describe **net battery flow**. Inverter AC LOAD includes power delivered through bypass; in DC mode a converter or solar charger can also feed the bus. Do not treat AC LOAD as battery drain or calculate converter output by subtracting non-simultaneous readings.

New mappings need repeated observations, a documented scale/range, an unknown/unavailable policy, sanitized regression fixtures, and framework tests before they become default entities. Keep unverified fields in diagnostics.
