"""Captured-frame and service-scoping tests; no Home Assistant install needed."""

import importlib.util
import json
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
INVERTING = bytes.fromhex("00000000b00458022c0202021b00d40051050000")
INVERTING_AUX = bytes.fromhex("6400150200000000000002000000002000000042")
BYPASS_RETURN = bytes.fromhex("b0045702b004570298015c011400fa0081050000")
BYPASS_RETURN_AUX = bytes.fromhex("6400f7012200000000000200000000000000004c")
SETTINGS = bytes.fromhex("0078002c01830019005802780014002c01005a00")


class ProtocolTests(unittest.TestCase):
    def test_repeated_controlled_mode_cycle(self):
        fixture = Path(__file__).parent / "fixtures/mode_comparison.json"
        for sample in json.loads(fixture.read_text()):
            with self.subTest(mode=sample["confirmed_panel_mode"]):
                result = protocol.parse_telemetry(
                    bytes.fromhex(sample["raw"]["2a03"]),
                    bytes.fromhex(sample["raw"]["2a04"]),
                    bytes.fromhex(sample["settings"]),
                )
                self.assertEqual(
                    result.values["power_path"], sample["confirmed_panel_mode"]
                )
                self.assertEqual(
                    result.values["ac_input_current"],
                    sample["expected_ac_input_current"],
                )
                for key, value in sample["expected"].items():
                    self.assertEqual(result.values[key], value)
                self.assertEqual(result.values["low_battery_recovery"], 13.1)

    def test_captured_live_sample(self):
        result = protocol.parse_telemetry(LIVE, AUX)
        self.assertEqual(result.values["ac_voltage"], 119.0)
        self.assertEqual(result.values["ac_frequency"], 60.0)
        self.assertEqual(result.values["ac_voltage_2"], 119.0)
        self.assertEqual(result.values["battery_voltage"], 14.52)
        self.assertEqual(result.values["load_power"], 414)
        self.assertEqual(result.values["load_apparent_power"], 498)
        self.assertEqual(result.values["load_percentage"], 24)
        self.assertEqual(result.values["ac_input_current"], 4.1)
        self.assertEqual(result.values["battery_level_provisional"], 100)
        self.assertEqual(result.raw["2a03"], LIVE.hex())
        self.assertEqual(result.words["2a03"][7], 257)
        self.assertNotIn("operating_mode", result.values)
        self.assertNotIn("battery_current", result.values)
        self.assertEqual(result.values["power_path"], "ac_bypass")

    def test_confirmed_dc_inverting_capture(self):
        result = protocol.parse_telemetry(INVERTING, INVERTING_AUX)
        self.assertEqual(result.values["ac_voltage"], 0.0)
        self.assertEqual(result.values["ac_frequency"], 0.0)
        self.assertEqual(result.values["ac_voltage_2"], 120.0)
        self.assertEqual(result.values["ac_frequency_2"], 60.0)
        self.assertEqual(result.values["battery_voltage"], 13.61)
        self.assertEqual(result.values["power_path"], "dc_inverting")
        self.assertEqual(result.values["load_power"], 514)
        self.assertEqual(result.values["ac_input_current"], 0.0)

    def test_return_to_bypass_separates_watts_from_va(self):
        result = protocol.parse_telemetry(BYPASS_RETURN, BYPASS_RETURN_AUX)
        self.assertEqual(result.values["power_path"], "ac_bypass")
        self.assertEqual(result.values["load_power"], 348)
        self.assertEqual(result.values["load_apparent_power"], 408)
        self.assertEqual(result.values["load_percentage"], 20)
        self.assertEqual(result.values["ac_input_current"], 3.4)
        self.assertEqual(result.values["ac_frequency"], 59.9)
        self.assertNotIn("ac_current_provisional", result.values)

    def test_power_path_does_not_guess_ambiguous_or_brownout_states(self):
        for values in [(120, 60, 110, 60), (40, 60, 120, 60), (0, 0, 120, 0)]:
            with self.subTest(values=values):
                self.assertIsNone(protocol.power_path(*values))
        self.assertEqual(protocol.power_path(0, 0, 0, 0), "no_ac_output")
        self.assertEqual(protocol.power_path(120, 60, 0, 0), "no_ac_output")

    def test_power_path_does_not_depend_on_unmapped_status_word(self):
        words = list(protocol.words_le(INVERTING))
        words[7] = 257
        result = protocol.parse_telemetry(struct.pack("<10H", *words), INVERTING_AUX)
        self.assertEqual(result.values["power_path"], "dc_inverting")

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

    def test_invalid_load_and_provisional_values_become_unknown(self):
        words = list(protocol.words_le(LIVE))
        words[4:7] = [65535, 65535, 65535]
        aux = [65535] + [0] * 9
        aux[2] = 65535
        result = protocol.parse_telemetry(
            struct.pack("<10H", *words), struct.pack("<10H", *aux)
        )
        for key in (
            "load_power",
            "load_apparent_power",
            "load_percentage",
            "battery_level_provisional",
            "ac_input_current",
        ):
            self.assertIsNone(result.values[key])
        self.assertEqual(result.values["battery_voltage"], 14.52)

    def test_settings_readbacks_match_current_fxc_screen(self):
        values = protocol.parse_settings(SETTINGS)
        self.assertEqual(
            values,
            {
                "low_battery_cutoff": 12.0,
                "low_battery_cutoff_delay": 300,
                "low_battery_recovery": 13.1,
                "power_save_time": 25,
                "configured_output_frequency": 60.0,
                "configured_output_voltage": 120,
                "output_power_limit": 2000,
                "output_power_limit_delay": 300,
                "utility_ac_under_voltage": 90,
            },
        )

    def test_unfamiliar_settings_remain_unknown_without_hiding_telemetry(self):
        for payload in (None, b"short", bytes(20), bytes([255]) * 20):
            with self.subTest(payload=payload):
                values = protocol.parse_telemetry(LIVE, AUX, payload).values
                self.assertEqual(values["load_power"], 414)
                self.assertTrue(
                    all(values[key] is None for key in protocol.SETTINGS_KEYS)
                )

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
                        protocol.uuid("2a0d"): Characteristic(SETTINGS),
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
    async def test_diagnostic_reads_are_scoped_and_exclude_identity(self):
        client = ReadOnlyClient()
        client.services.fields[protocol.LIVE_SERVICE].fields[protocol.uuid("2a05")] = (
            Characteristic(bytes.fromhex("01020304"))
        )
        details = await protocol.read_diagnostic_fields(client)
        self.assertEqual(details["1910/2a05"], {"hex": "01020304"})
        self.assertEqual(details["1911/2a11"], {"error_type": "ProtocolError"})
        self.assertNotIn("1910/2a02", details)
        self.assertEqual(len(client.reads), 2)

    async def test_scoped_read_with_duplicate_characteristic_uuid(self):
        client = ReadOnlyClient()
        identity = await protocol.read_identity(client)
        result = await protocol.read_telemetry(client)
        self.assertEqual(identity.serial, "TESTSERIAL0001")
        self.assertEqual(result.values["battery_voltage"], 14.52)
        self.assertEqual(len(client.reads), 6)

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
