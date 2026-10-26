# Xantrex Freedom X BLE

Experimental **read-only** Home Assistant integration for a **Freedom X 2000 12 V** inverter with a **Freedom X Bluetooth Remote Panel**. Independent community software; not affiliated with Xantrex.

[![Tests](https://github.com/sators/ha-xantrex-freedom-x/actions/workflows/tests.yml/badge.svg)](https://github.com/sators/ha-xantrex-freedom-x/actions/workflows/tests.yml)

**[Install through HACS](#install-with-hacs-recommended)** · [Report a problem](https://github.com/sators/ha-xantrex-freedom-x/issues) · [Protocol mapping](#mapping-status)

This is a protocol prototype built from device captures. Parser and fake-client tests are provided. A live Home Assistant installation and reads from the inverter still need verification. Do not treat the supplied sample frames as live delivery evidence.

## What it does

- Uses Home Assistant's Bluetooth adapters, including connectable proxies where supported by the device.
- Checks that the device reports manufacturer `Xantrex` and model `Freedom X Remote`.
- Polls every 30 seconds by default, releasing the connection after each sample.
- Provides AC voltage, AC frequency, battery voltage, and telemetry availability.
- Preserves the two live raw frames in a redacted diagnostics download for further protocol work.
- Marks measurement entities unavailable when a poll fails.

No inverter controls, configuration writes, firmware updates, automatic pairing, or mode-changing commands are implemented. Phone apps may compete for the connection; disconnect FXC Control and nRF Connect during setup. To use the phone app again, disable this integration temporarily if it repeatedly competes for the connection.

## Mapping status

All numeric offsets below are byte offsets in the characteristic value, interpreted as unsigned 16-bit little-endian integers. The app screenshots and packet captures were taken several minutes apart, so dynamic power/current values are not simultaneous validation.

| Service / characteristic | Offset | Interpretation | Evidence / limitation |
| --- | ---: | --- | --- |
| `180A / 2A29` | — | Manufacturer, ASCII | Reads `Xantrex` |
| `180A / 2A24` | — | Remote model, ASCII | Reads `Freedom X Remote` |
| `1910 / 2A02` | — | Serial number, ASCII | Matches the app's device identifier |
| `1910 / 2A03` | 0 | AC voltage ÷ 10 | Raw 1190 and app 119 V in bypass; direction not independently verified |
| `1910 / 2A03` | 2 | AC frequency ÷ 10 | Raw 600 and app 60 Hz |
| `1910 / 2A03` | 4, 6 | Second AC voltage/frequency pair | Same values in bypass; entities disabled by default |
| `1910 / 2A03` | 16 | Battery voltage ÷ 100 | Raw 1452 consistent with rounded app 14.5 V |
| `1910 / 2A03` | 8 | **Provisional** AC power in W | Raw 498; later app sample 425 W; needs simultaneous validation |
| `1910 / 2A03` | 10 | **Provisional** AC current ÷ 100 | Raw 414 consistent with later app 4.1 A |
| `1910 / 2A03` | 12 | **Provisional** load percentage | Raw and app both 24%; needs additional operating points |
| `1910 / 2A04` | 0 | **Provisional** reported battery level | Raw/app both 100%; not validated away from full; prefer a BMS or shunt |

Provisional entities are omitted unless explicitly opted into during setup. They do not declare a statistics state class. Operating-mode flags, battery current, fault bits, temperatures, configuration blocks, and version-field meanings remain unmapped. No `AC-BYPASS` mode is inferred from a single captured flag value.

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
4. Search HACS for **Xantrex Freedom X BLE (Experimental)**, open it, and choose **Download**. When no release is available, HACS installs the default branch.
5. **Restart Home Assistant Core**. Downloading through HACS installs the files; the restart makes the integration available to Home Assistant.
6. Continue with **Configure the integration** below.

These steps follow the [HACS custom repository instructions](https://www.hacs.xyz/docs/faq/custom_repositories/). No YAML configuration, SSH access, or manual file copying is needed for a HACS installation.

### Configure the integration

1. Disconnect **FXC Control** and **nRF Connect** from the panel so Home Assistant can connect. Leave the panel and Home Assistant Bluetooth enabled.
2. Open **Settings → Devices & services → Add integration**, then search for **Xantrex Freedom X BLE (Experimental)**. A matching Bluetooth advertisement may also offer discovery.
3. Enter the panel's **Bluetooth MAC address**, choose a polling interval (30 seconds by default, 30–600 seconds allowed), and leave provisional sensors off for the first connection. The Bluetooth address is different from the serial number or `ID…` device name; find it in Home Assistant's Bluetooth advertisement monitor.
4. Setup reads the panel's identity and one telemetry sample. After success, open its device page and confirm AC voltage, frequency, battery voltage, and telemetry availability.
5. Compare readings with the panel display or a separate FXC Control session before relying on them in dashboards or automations. Disable this integration temporarily while using the phone app if the two compete for the connection.

The integration needs no cloud account or credentials. Poll interval and provisional-sensor selection are setup parameters; changing them currently requires removing the integration entry and adding it again. HACS does not need to be removed or reinstalled.

### Updates through HACS

Open the integration in HACS and download an offered update, then **restart Home Assistant Core**. Read the changelog or commit notes first: protocol mappings may change while the integration is experimental. HACS manages the component files; **Devices & services** manages the configured device.

### Manual installation (alternative)

1. Copy `custom_components/xantrex_freedom_x_ble` into your Home Assistant configuration directory's `custom_components/` folder.
2. Restart Home Assistant Core so it can discover the new integration.
3. Follow **Configure the integration** above.

## Troubleshooting

- **Not found in HACS:** add the full repository URL under **Custom repositories**, with type **Integration**. Searching the default catalog alone will not find it.
- **Downloaded but absent from Add integration:** restart Home Assistant Core, then refresh the browser. Check Home Assistant logs if it still does not appear.
- **Cannot connect / telemetry unavailable:** disconnect phone apps, check Bluetooth range and available proxy connection slots, and confirm Home Assistant can see the panel's advertisement. The integration releases its own connection after every poll.
- **Unsupported device or payload:** confirm the model and manufacturer, then report the firmware and a reviewed diagnostics export. The parser deliberately rejects unfamiliar frame layouts rather than producing plausible-looking values.
- **Power or load sensors missing:** these are provisional and require an explicit opt-in during setup. Mode, battery current, faults, and settings are not implemented.

## Diagnostics and removal

Use **Download diagnostics** on the integration entry to retrieve raw live frames, their decoded words, and the last successful-read time. The integration's diagnostics omit Bluetooth addresses and serial numbers; review exports before sharing. Logs from Home Assistant or third-party tools can contain identifiers independently of this integration.

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
