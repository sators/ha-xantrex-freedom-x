"""Captured-frame and service-scoping tests; no Home Assistant install needed."""

import importlib.util
import struct
import sys
import unittest
from pathlib import Path

MODULE = (
    Path(__file__).parents[1] / "custom_components/xantrex_freedom_x_ble/protocol.py"
)
spec = importlib.util.spec_from_file_location("xantrex_protocol_under_test", MODULE)
protocol = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = protocol
spec.loader.exec_module(protocol)

LIVE = bytes.fromhex("A604 5802 A604 5802 F201 9E01 1800 0101 AC05 0000")
AUX = bytes.fromhex("6400 0E02 2900 0000 0000 0200 0000 0000 0000 004C")


class ProtocolTests(unittest.TestCase):
    def test_captured_live_sample(self):
        result = protocol.parse_telemetry(LIVE, AUX)
        self.assertEqual(result.values["ac_voltage"], 119.0)
        self.assertEqual(result.values["ac_frequency"], 60.0)
        self.assertEqual(result.values["ac_voltage_2"], 119.0)
        self.assertEqual(result.values["battery_voltage"], 14.52)
        self.assertEqual(result.values["ac_current_provisional"], 4.14)
        self.assertEqual(result.values["ac_power_provisional"], 498)
        self.assertEqual(result.values["load_provisional"], 24)
        self.assertEqual(result.values["battery_level_provisional"], 100)
        self.assertEqual(result.raw["2a03"], LIVE.hex())
        self.assertEqual(result.words["2a03"][7], 257)
        self.assertNotIn("operating_mode", result.values)
        self.assertNotIn("battery_current", result.values)

    def test_rejects_truncation_and_extensions(self):
        for length in (0, 1, 19, 21, 40):
            with self.subTest(length=length), self.assertRaises(protocol.ProtocolError):
                protocol.parse_telemetry(bytes(length), AUX)
            with (
                self.subTest(aux_length=length),
                self.assertRaises(protocol.ProtocolError),
            ):
                protocol.parse_telemetry(LIVE, bytes(length))

    def test_rejects_blank_sentinel_and_unsupported_voltage(self):
        for frame in (bytes(20), bytes([255]) * 20):
            with self.assertRaises(protocol.ProtocolError):
                protocol.parse_telemetry(frame, AUX)
        words = list(protocol.words_le(LIVE))
        words[8] = 2904
        with self.assertRaises(protocol.ProtocolError):
            protocol.parse_telemetry(struct.pack("<10H", *words), AUX)

    def test_zero_ac_is_valid_when_battery_remains_present(self):
        words = [0] * 10
        words[8] = 1280
        result = protocol.parse_telemetry(struct.pack("<10H", *words), bytes(20))
        self.assertEqual(result.values["ac_voltage"], 0)
        self.assertEqual(result.values["ac_frequency"], 0)
        self.assertEqual(result.values["battery_voltage"], 12.8)

    def test_invalid_provisional_values_become_unknown(self):
        words = list(protocol.words_le(LIVE))
        words[4:7] = [65535, 65535, 65535]
        aux = [65535] + [0] * 9
        result = protocol.parse_telemetry(
            struct.pack("<10H", *words), struct.pack("<10H", *aux)
        )
        for key in (
            "ac_power_provisional",
            "ac_current_provisional",
            "load_provisional",
            "battery_level_provisional",
        ):
            self.assertIsNone(result.values[key])
        self.assertEqual(result.values["battery_voltage"], 14.52)

    def test_identity_text_and_invalid_encoding(self):
        self.assertEqual(
            protocol.text_value(b"Freedom X Remote\x00  "), "Freedom X Remote"
        )
        with self.assertRaises(protocol.ProtocolError):
            protocol.text_value(b"\xff")


class Characteristic:
    def __init__(self, payload, properties=("read",)):
        self.payload = payload
        self.properties = properties


class Service:
    def __init__(self, fields):
        self.fields = fields

    def get_characteristic(self, uuid):
        return self.fields.get(uuid)


class FakeServices:
    def __init__(self, fields):
        self.fields = fields

    def get_service(self, uuid):
        return self.fields.get(uuid)

    def get_characteristic(self, uuid):
        raise AssertionError("Global lookup is ambiguous and must never be used")


class ReadOnlyClient:
    def __init__(self, manufacturer=b"Xantrex", model=b"Freedom X Remote"):
        self.reads = []
        self.services = FakeServices(
            {
                protocol.INFO_SERVICE: Service(
                    {
                        protocol.uuid("2a29"): Characteristic(manufacturer),
                        protocol.uuid("2a24"): Characteristic(model),
                    }
                ),
                protocol.LIVE_SERVICE: Service(
                    {
                        protocol.uuid("2a02"): Characteristic(b"TESTSERIAL0001      "),
                        protocol.uuid("2a03"): Characteristic(LIVE),
                        protocol.uuid("2a04"): Characteristic(AUX),
                    }
                ),
                protocol.uuid("1800"): Service(
                    {
                        protocol.uuid("2a03"): Characteristic(b"WRONG SERVICE"),
                    }
                ),
            }
        )

    async def read_gatt_char(self, characteristic):
        self.reads.append(characteristic)
        return characteristic.payload

    async def write_gatt_char(self, *args, **kwargs):
        raise AssertionError("No writes are permitted")

    async def start_notify(self, *args, **kwargs):
        raise AssertionError("No subscriptions are permitted")


class ReadTests(unittest.IsolatedAsyncioTestCase):
    async def test_scoped_read_with_duplicate_characteristic_uuid(self):
        client = ReadOnlyClient()
        identity = await protocol.read_identity(client)
        result = await protocol.read_telemetry(client)
        self.assertEqual(identity.serial, "TESTSERIAL0001")
        self.assertEqual(result.values["battery_voltage"], 14.52)
        self.assertEqual(len(client.reads), 5)

    async def test_wrong_manufacturer_or_model_is_rejected(self):
        for client in (
            ReadOnlyClient(manufacturer=b"Other"),
            ReadOnlyClient(model=b"Other"),
        ):
            with self.assertRaises(protocol.UnsupportedDeviceError):
                await protocol.read_identity(client)

    async def test_missing_service_and_nonreadable_characteristic(self):
        client = ReadOnlyClient()
        del client.services.fields[protocol.LIVE_SERVICE]
        with self.assertRaises(protocol.ProtocolError):
            await protocol.read_telemetry(client)
        client = ReadOnlyClient()
        client.services.fields[protocol.LIVE_SERVICE].fields[
            protocol.uuid("2a03")
        ].properties = ("write",)
        with self.assertRaises(protocol.ProtocolError):
            await protocol.read_telemetry(client)
        self.assertEqual(client.reads, [])


if __name__ == "__main__":
    unittest.main()
