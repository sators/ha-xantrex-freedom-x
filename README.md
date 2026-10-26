# Xantrex Freedom X BLE

Experimental **read-only** Home Assistant integration for a **Freedom X 2000 12 V** inverter with a **Freedom X Bluetooth Remote Panel**. Independent community software; not affiliated with Xantrex.

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

## Install manually

1. Copy `custom_components/xantrex_freedom_x_ble` into your Home Assistant configuration directory's `custom_components/` folder.
2. Restart Home Assistant Core so it can discover the new integration.
3. Open **Settings → Devices & services → Add integration**, then search for **Xantrex Freedom X BLE (Experimental)**. A matching Bluetooth advertisement may also offer discovery.
4. Enter the remote's Bluetooth address, choose a polling interval, and leave provisional sensors off for the first connection.
5. Compare the live readings to FXC Control before adding them to dashboards or automations.

The address is available in Home Assistant's Bluetooth advertisement monitor. The integration uses existing Home Assistant Bluetooth dependencies and requires no cloud account.

### HACS custom repository

Add `https://github.com/sators/ha-xantrex-freedom-x` to HACS as an **Integration** custom repository, install it, and restart Home Assistant. This repository has not been submitted to the default HACS catalog.

## Diagnostics and removal

Use **Download diagnostics** on the integration entry to retrieve raw live frames, their decoded words, and the last successful-read time. The integration's diagnostics omit Bluetooth addresses and serial numbers; review exports before sharing. Logs from Home Assistant or third-party tools can contain identifiers independently of this integration.

Disable or remove the integration through **Devices & services** to stop polling. To remove the software, remove the integration entry, delete its custom-component folder, and restart Home Assistant.

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
