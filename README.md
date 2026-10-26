# Xantrex Freedom X BLE

Experimental **read-only** Home Assistant integration for a **Freedom X 2000 12 V** inverter with a **Freedom X Bluetooth Remote Panel**. Independent community software; not affiliated with Xantrex.

[![Tests](https://github.com/sators/ha-xantrex-freedom-x/actions/workflows/tests.yml/badge.svg)](https://github.com/sators/ha-xantrex-freedom-x/actions/workflows/tests.yml)

**[Install through HACS](#install-with-hacs-recommended)** · [Report a problem](https://github.com/sators/ha-xantrex-freedom-x/issues) · [Protocol mapping](#mapping-status)

This is an experimental protocol implementation built from device captures. HACS release installation, device identity, live telemetry reads, and repeated polling have been verified on one Freedom X 2000 12 V setup with Home Assistant 2026.10.3. Parser and framework tests are also provided. AC bypass and brief DC inverter operation have been compared on that setup. Other hardware, firmware, operating states, and the reported battery percentage away from 100% still need validation.

## What it does

- Uses Home Assistant's Bluetooth adapters, including connectable proxies where supported by the device.
- Checks that the device reports manufacturer `Xantrex` and model `Freedom X Remote`.
- Polls every 30 seconds by default, releasing the connection after each sample.
- Provides AC input/output voltage and frequency, real LOAD power (W), reported load percentage, battery voltage, and telemetry availability.
- Infers the power path from the validated input/output measurements: AC bypass, DC to AC inverting, or no AC output. Ambiguous states remain unknown.
- Offers apparent load power (VA) as a disabled diagnostic entity and reported battery percentage as an opt-in provisional diagnostic.
- Preserves the two live raw frames in a redacted diagnostics download for further protocol work.
- Marks measurement entities unavailable when a poll fails.

No inverter controls, configuration writes, firmware updates, automatic pairing, or mode-changing commands are implemented. Phone apps may compete for the connection; disconnect FXC Control and nRF Connect during setup. To use the phone app again, disable this integration temporarily if it repeatedly competes for the connection.

## Mapping status

All numeric offsets below are byte offsets, interpreted as unsigned 16-bit little-endian integers. A controlled bypass → inverter → bypass comparison distinguished input from output. A close app/frame comparison distinguished real watts from apparent volt-amperes; measurements were about one minute apart, not simultaneous.

| Service / characteristic | Offset | Interpretation | Evidence / limitation |
| --- | ---: | --- | --- |
| `180A / 2A29` | — | Manufacturer, ASCII | Reads `Xantrex` |
| `180A / 2A24` | — | Remote model, ASCII | Reads `Freedom X Remote` |
| `1910 / 2A02` | — | Serial number, ASCII | Matches the app's device identifier |
| `1910 / 2A03` | 0, 2 | AC **input** V ÷ 10, Hz ÷ 10 | Dropped to 0 V / 0 Hz in confirmed inverter operation |
| `1910 / 2A03` | 4, 6 | AC **output** V ÷ 10, Hz ÷ 10 | Remained 120 V / 60 Hz in inverter operation; input/output matched again in bypass |
| `1910 / 2A03` | 8 | Apparent load power, VA | Frame 408 VA consistent with app 120 V × 3.4 A |
| `1910 / 2A03` | 10 | Real LOAD power, W | App 350 W, followed by frame 348 W; original candidate current mapping was incorrect |
| `1910 / 2A03` | 12 | Reported load percentage | App/frame both 20%; earlier capture 24%; do not derive it from real watts |
| `1910 / 2A03` | 16 | DC battery voltage ÷ 100 | Raw 1452 consistent with app 14.5 V; fell to 13.59–13.61 V in inverter captures |
| `1910 / 2A04` | 0 | **Provisional** reported battery percentage | Raw/app both 100%; not validated below full; prefer a BMS or shunt |

**Power path is an inference, not a decoded mode flag.** A live 80–150 V / 45–65 Hz output with absent input (≤5 V / ≤1 Hz) indicates DC inverting. Live matching input/output (within 5 V / 1 Hz) indicates AC bypass, consistent with the inverter's AC-priority behavior. An absent output indicates no AC output; other combinations remain unknown. Failed polls make entities unavailable. These bounds cover the tested 120 V installation; they are not inverter protection settings.

DC inverting means the inverter draws from the **12 V bus**, which may also receive converter or solar power. It does not prove the battery is discharging. Use the BMS/shunt's signed current and power for net battery flow. AC input could be shore power or a generator; these measurements do not distinguish them.

Battery percentage is omitted unless opted into during setup and has no statistics state class. Raw mode flags, DC current, fault bits, temperatures, configuration blocks, and version fields remain unmapped. Diagnostics exports now perform an additional, bounded read of the known custom-service data blocks for comparison; this does not happen during normal polling. No characteristic writes are used.

### Upgrading from 0.1.x

Version 0.2.0 removes the incorrect **provisional AC current** and **provisional AC power** interpretations. Use the new **Load power** (W), **Load apparent power** (VA), and **Load percentage** entities instead. Old provisional entities may remain unavailable in the entity registry; history is not migrated between different physical quantities. The existing AC voltage/frequency entity IDs are retained and now explicitly named **input**. Previously disabled channel-2 entities are now named **output**; existing installations must enable them in the device's disabled-entities list if needed.

The nRF Connect labels (for example `Reconnection Address`, `Date Time`, `Time Zone`) are standard names associated with characteristic UUIDs. Under custom services `1910` and `1911`, they must not be assumed to describe the actual Xantrex payload. Some UUIDs also occur in standard services; the reader resolves characteristics **within the correct service**.

Only the observed 20-byte payload layout and 12 V voltage range are accepted. Other models, firmware, 24 V systems, and sustained inverter operation have not been verified.

## Requirements and compatibility

- Home Assistant **2026.10.0 or newer**; framework tests target 2026.10.3.
- A **Freedom X Bluetooth Remote Panel** connected to the inverter. A non-Bluetooth panel alone will not work.
- A working Home Assistant Bluetooth adapter or connectable Bluetooth proxy within range of the panel. Set up Home Assistant's [Bluetooth integration](https://www.home-assistant.io/integrations/bluetooth/) first.
- The protocol currently targets the captured **Freedom X 2000, 12 V** setup. Other Freedom X/XC models and firmware are unverified; see the mapping limitations below.

## Install with HACS (recommended)

This integration is available as a **HACS custom repository**. It is not included in the default HACS catalog. [Install and configure HACS](https://www.hacs.xyz/docs/use/) first if needed.

1. Open **HACS** in Home Assistant.
2. Open the **⋮ menu → Custom repositories**.
3. Enter `https://github.com/sators/ha-xantrex-freedom-x`, select **Integration** as the type, and click **Add**.
4. Search HACS for **Xantrex Freedom X BLE (Experimental)**, open it, and choose **Download**. Select the latest published release (**v0.2.0 or newer**). HACS can also install the default branch for development, but a release gives a reproducible version.
5. **Restart Home Assistant Core**. Downloading through HACS installs the files; the restart makes the integration available to Home Assistant.
6. Continue with **Configure the integration** below.

These steps follow the [HACS custom repository instructions](https://www.hacs.xyz/docs/faq/custom_repositories/). No YAML configuration, SSH access, or manual file copying is needed for a HACS installation.

### Configure the integration

1. Disconnect **FXC Control** and **nRF Connect** from the panel so Home Assistant can connect. Leave the panel and Home Assistant Bluetooth enabled.
2. Open **Settings → Devices & services → Add integration**, then search for **Xantrex Freedom X BLE (Experimental)**. A matching Bluetooth advertisement may also offer discovery.
3. Enter the panel's **Bluetooth MAC address**, choose a polling interval (30 seconds by default, 30–600 seconds allowed), and leave provisional sensors off for the first connection. The Bluetooth address is different from the serial number or `ID…` device name; find it in Home Assistant's Bluetooth advertisement monitor.
4. Setup reads the panel's identity and one telemetry sample. After success, open its device page and confirm input/output voltage and frequency, LOAD watts, power path, battery voltage, and telemetry availability.
5. Compare readings with the panel display or a separate FXC Control session before relying on them in dashboards or automations. Disable this integration temporarily while using the phone app if the two compete for the connection.

The integration needs no cloud account or credentials. Poll interval and provisional-sensor selection are setup parameters; changing them currently requires removing the integration entry and adding it again. HACS does not need to be removed or reinstalled.

### Updates through HACS

Open the integration in HACS and download an offered update, then **restart Home Assistant Core**. Read the [changelog](CHANGELOG.md) or commit notes first: protocol mappings may change while the integration is experimental. HACS manages the component files; **Devices & services** manages the configured device. To fetch the current default branch manually, open the integration's **⋮ menu → Update information**, then **Redownload**.

### Manual installation (alternative)

1. Copy `custom_components/xantrex_freedom_x_ble` into your Home Assistant configuration directory's `custom_components/` folder.
2. Restart Home Assistant Core so it can discover the new integration.
3. Follow **Configure the integration** above.

## Troubleshooting

- **Not found in HACS:** add the full repository URL under **Custom repositories**, with type **Integration**. Searching the default catalog alone will not find it.
- **Downloaded but absent from Add integration:** restart Home Assistant Core, then refresh the browser. Check Home Assistant logs if it still does not appear.
- **Cannot connect / telemetry unavailable:** disconnect phone apps, check Bluetooth range and available proxy connection slots, and confirm Home Assistant can see the panel's advertisement. The integration releases its own connection after every poll.
- **Unsupported device or payload:** confirm the model and manufacturer, then report the firmware and a reviewed diagnostics export. The parser deliberately rejects unfamiliar frame layouts rather than producing plausible-looking values.
- **Output sensors missing after upgrading:** enable the previously disabled channel-2 entities on the device page. Load power and load percentage are enabled by default in 0.2.0. Battery percentage remains opt-in; direct mode flags, DC current, faults, and settings remain unmapped.

## Diagnostics and removal

Use **Download diagnostics** on the integration entry to retrieve the latest periodic sample and an on-demand extended capture. The `protocol_capture.observed_at` timestamp belongs to the fresh capture; `last_successful_read` belongs to routine polling. Disconnect phone apps first. A failed capture has an error type rather than presenting stale bytes as fresh. The integration's diagnostics omit Bluetooth addresses and serial numbers; review exports before sharing. Logs from Home Assistant or third-party tools can contain identifiers independently of this integration.

Disable or remove the integration through **Devices & services** to stop polling. To uninstall completely, remove its entry there, remove the downloaded repository through HACS, and restart Home Assistant Core. For a manual installation, delete its custom-component folder instead of removing it through HACS.

## Help validate the protocol

[Open an issue](https://github.com/sators/ha-xantrex-freedom-x/issues) with the inverter model, DC system voltage, remote-panel firmware, Home Assistant version, adapter/proxy type, and the problem or observed mismatch. Useful evidence includes reviewed diagnostics and readings from the panel or FXC Control taken as close together as possible. Note whether the inverter was in bypass or inverter operation; never interrupt power or change protective settings just to collect a sample.

Remove serial numbers, Bluetooth addresses, and other installation details before posting screenshots or logs. Do not post passwords or Home Assistant tokens. Compatibility reports for additional hardware are welcome, but one successful connection does not validate every field or operating mode.

## Development

Run the tests using Python 3.11 or later:

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q custom_components
```

Tests cover the captured numeric values, truncated frames, unsupported layouts, invalid measurements, wrong-device rejection, and service-scoped reads with duplicate characteristic UUIDs. They do not simulate RF range, BlueZ, a Home Assistant restart, or handset contention.

GitHub Actions also imports the integration against Home Assistant 2026.10.3 and checks the Bluetooth lifecycle with a fake radio: cleanup after failure, serial mismatch, opt-in entities, and unavailable-state handling. That framework test is separate from live hardware verification.

Keep installation-specific addresses, serials, diagnostics, and screenshots under a gitignored `private/` folder. The public fixtures deliberately replace the device serial.

## References

- [Home Assistant Bluetooth integration APIs](https://contributors.home-assistant.io/core/integrations/bluetooth/)
- [Xantrex Freedom X Bluetooth Remote Panel](https://xantrex.com/products/accessories/freedom-x-bluetooth-remote-panel/)
- [Xantrex remote panel user guide](https://xantrex.com/wp-content/uploads/2021/12/976-0367-01-01_F.pdf)
