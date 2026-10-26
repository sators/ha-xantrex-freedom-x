"""Read-only protocol evidence from a Freedom X 2000 Bluetooth remote.

The remote reuses standard characteristic UUIDs for proprietary payloads.
Always resolve a characteristic within its service, never by UUID alone.
No command, setting write, pairing, or notification subscription is implemented.
"""

import asyncio
import struct
from dataclasses import dataclass
from typing import Any


def uuid(short: str) -> str:
    return f"0000{short.lower()}-0000-1000-8000-00805f9b34fb"


INFO_SERVICE = uuid("180a")
LIVE_SERVICE = uuid("1910")


class ProtocolError(ValueError):
    """The payload cannot be interpreted with the observed protocol."""


class UnsupportedDeviceError(ProtocolError):
    """The connected device is not a supported Xantrex remote."""


@dataclass(frozen=True)
class Identity:
    manufacturer: str
    model: str
    serial: str


@dataclass(frozen=True)
class Telemetry:
    values: dict[str, float | int | str | None]
    words: dict[str, tuple[int, ...]]
    raw: dict[str, str]


def words_le(payload: bytes) -> tuple[int, ...]:
    """The observed custom frames are exactly twenty bytes."""
    if len(payload) != 20:
        raise ProtocolError(f"Expected 20 bytes, received {len(payload)}")
    return struct.unpack("<10H", payload)


def text_value(payload: bytes) -> str:
    try:
        return payload.decode("ascii").strip("\x00 \r\n")
    except UnicodeDecodeError as err:
        raise ProtocolError("Device information is not ASCII") from err


def power_path(input_v: float, input_hz: float, output_v: float, output_hz: float):
    """Infer the power path from independently observed AC input/output pairs.

    This is not a decoded status flag. The Freedom X prioritizes valid AC input
    and bypasses it to the output. With no AC input and a live AC output, it is
    converting DC to AC. The DC source can include a converter or solar charger.
    Ambiguous transitions or unfamiliar operating points remain unknown.
    """
    output_absent = output_v <= 5 and output_hz <= 1
    input_absent = input_v <= 5 and input_hz <= 1
    output_live = 80 <= output_v <= 150 and 45 <= output_hz <= 65
    input_live = 80 <= input_v <= 150 and 45 <= input_hz <= 65
    if output_absent:
        return "no_ac_output"
    if output_live and input_absent:
        return "dc_inverting"
    if (
        output_live
        and input_live
        and abs(input_v - output_v) <= 5
        and abs(input_hz - output_hz) <= 1
    ):
        return "ac_bypass"
    return None


def parse_telemetry(live: bytes, auxiliary: bytes) -> Telemetry:
    """Decode observed scales; preserve unknown bytes without assigning meaning.

    AC pair direction was checked in AC bypass and confirmed inverter operation:
    the input pair dropped to zero while output remained 120 V / 60 Hz.
    No meaning is assigned to the raw status words or DC-current fields.
    """
    w = words_le(live)
    aux = words_le(auxiliary)
    if not 500 <= w[8] <= 1800:
        raise ProtocolError(
            "Unexpected battery-voltage encoding for the 12 V prototype"
        )
    if any(w[i] > 3000 for i in (0, 2)) or any(w[i] > 700 for i in (1, 3)):
        raise ProtocolError("AC fields do not match the observed encoding")

    values = {
        "ac_voltage": w[0] / 10,
        "ac_frequency": w[1] / 10,
        "ac_voltage_2": w[2] / 10,
        "ac_frequency_2": w[3] / 10,
        "battery_voltage": w[8] / 100,
        "power_path": power_path(w[0] / 10, w[1] / 10, w[2] / 10, w[3] / 10),
        # Close app comparison: 350 W / 20%, followed by 348 W / 20%.
        # Apparent power (408 VA) also agreed with the app's 120 V * 3.4 A.
        "load_apparent_power": w[4] if w[4] <= 10000 else None,
        "load_power": w[5] if w[5] <= 10000 else None,
        "load_percentage": w[6] if w[6] <= 100 else None,
        # Not validated away from full charge; prefer a BMS or shunt.
        "battery_level_provisional": aux[0] if aux[0] <= 100 else None,
    }
    return Telemetry(
        values=values,
        words={"2a03": w, "2a04": aux},
        raw={"2a03": live.hex(), "2a04": auxiliary.hex()},
    )


async def read_characteristic(client: Any, service_uuid: str, short: str) -> bytes:
    """Resolve duplicate UUIDs safely and issue only a GATT read."""
    service = client.services.get_service(service_uuid)
    if service is None:
        raise ProtocolError(f"Required service {service_uuid} is missing")
    characteristic = service.get_characteristic(uuid(short))
    if characteristic is None or "read" not in characteristic.properties:
        raise ProtocolError(
            f"Characteristic {short} is not readable in the required service"
        )
    return bytes(await client.read_gatt_char(characteristic))


async def read_identity(client: Any) -> Identity:
    manufacturer = text_value(await read_characteristic(client, INFO_SERVICE, "2a29"))
    model = text_value(await read_characteristic(client, INFO_SERVICE, "2a24"))
    if manufacturer.casefold() != "xantrex" or model.casefold() != "freedom x remote":
        raise UnsupportedDeviceError(
            "Expected manufacturer Xantrex and model Freedom X Remote"
        )
    serial = text_value(await read_characteristic(client, LIVE_SERVICE, "2a02"))
    if not serial or not serial.isascii() or not serial.isalnum():
        raise ProtocolError("The remote did not return a valid serial number")
    return Identity(manufacturer, model, serial)


async def read_telemetry(client: Any) -> Telemetry:
    live = await read_characteristic(client, LIVE_SERVICE, "2a03")
    auxiliary = await read_characteristic(client, LIVE_SERVICE, "2a04")
    return parse_telemetry(live, auxiliary)


async def read_diagnostic_fields(client: Any) -> dict[str, dict[str, str]]:
    """Read only the observed custom data blocks, on explicit diagnostics export.

    Do not enumerate/read arbitrary services or the serial characteristic. These
    bytes have no entity meanings until compared against the manufacturer's app.
    An optional read failure must not invalidate the normal telemetry sample.
    """
    result = {}
    for service_short, fields in (
        ("1910", range(0x2A01, 0x2A0F)),
        ("1911", range(0x2A11, 0x2A15)),
    ):
        for field in fields:
            if field in (0x2A02, 0x2A03, 0x2A04):
                continue
            short = f"{field:04x}"
            key = f"{service_short}/{short}"
            try:
                async with asyncio.timeout(2):
                    payload = await read_characteristic(
                        client, uuid(service_short), short
                    )
                result[key] = {"hex": payload.hex()}
            except (TimeoutError, OSError, ProtocolError) as err:
                result[key] = {"error_type": type(err).__name__}
    return result
