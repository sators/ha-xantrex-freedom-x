"""Exercise real Home Assistant imports and our BLE lifecycle with a fake radio."""

import asyncio
import importlib.util
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bleak.exc import BleakError

from custom_components.xantrex_freedom_x_ble import binary_sensor, config_flow, sensor
from custom_components.xantrex_freedom_x_ble.coordinator import (
    XantrexCoordinator,
    fetch_snapshot,
)
from custom_components.xantrex_freedom_x_ble.protocol import ProtocolError
from homeassistant.components.bluetooth.match import IntegrationMatcher
from homeassistant.helpers.update_coordinator import UpdateFailed

# Reuse the read-only fake whose global UUID lookup deliberately fails.
spec = importlib.util.spec_from_file_location(
    "capture_tests", Path(__file__).parents[1] / "tests/test_protocol.py"
)
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = capture.ReadOnlyClient()
        self.client.disconnect = AsyncMock()
        self.device = object()
        self.device_patch = patch(
            "custom_components.xantrex_freedom_x_ble.coordinator.bluetooth.async_ble_device_from_address",
            return_value=self.device,
        )
        self.connector_patch = patch(
            "custom_components.xantrex_freedom_x_ble.coordinator.establish_connection",
            new=AsyncMock(return_value=self.client),
        )
        self.device_patch.start()
        self.connector = self.connector_patch.start()
        self.addCleanup(self.device_patch.stop)
        self.addCleanup(self.connector_patch.stop)

    async def test_successful_read_releases_connection(self):
        result = await fetch_snapshot(object(), "AA:BB:CC:DD:EE:FF")
        self.assertEqual(result.telemetry.values["battery_voltage"], 14.52)
        self.client.disconnect.assert_awaited_once()
        self.assertFalse(self.connector.call_args.kwargs["pair"])
        self.assertEqual(len(self.client.reads), 6)

    async def test_parse_failure_still_releases_connection(self):
        field = self.client.services.fields[capture.protocol.LIVE_SERVICE]
        field.fields[capture.protocol.uuid("2a03")].payload = b"truncated"
        with self.assertRaises(ProtocolError):
            await fetch_snapshot(object(), "AA:BB:CC:DD:EE:FF")
        self.client.disconnect.assert_awaited_once()

    async def test_read_timeout_still_releases_connection(self):
        self.client.read_gatt_char = AsyncMock(side_effect=TimeoutError)
        with self.assertRaises(TimeoutError):
            await fetch_snapshot(object(), "AA:BB:CC:DD:EE:FF")
        self.client.disconnect.assert_awaited_once()

    async def test_missing_adapter_does_not_try_direct_scanning(self):
        with (
            patch(
                "custom_components.xantrex_freedom_x_ble.coordinator.bluetooth.async_ble_device_from_address",
                return_value=None,
            ),
            self.assertRaises(BleakError),
        ):
            await fetch_snapshot(object(), "AA:BB:CC:DD:EE:FF")
        self.connector.assert_not_awaited()

    async def test_changed_serial_rejects_sample(self):
        coordinator = XantrexCoordinator.__new__(XantrexCoordinator)
        coordinator.hass = object()
        coordinator._read_lock = asyncio.Lock()
        coordinator.entry = SimpleNamespace(
            data={"address": "AA:BB:CC:DD:EE:FF", "serial": "DIFFERENT"}
        )
        with self.assertRaises(UpdateFailed):
            await XantrexCoordinator._async_update_data(coordinator)
        self.client.disconnect.assert_awaited_once()

    async def test_extended_capture_is_explicit_and_releases_connection(self):
        result = await fetch_snapshot(
            object(), "AA:BB:CC:DD:EE:FF", capture_details=True
        )
        self.assertIn("1910/2a01", result.diagnostic_fields)
        self.assertNotIn("1910/2a02", result.diagnostic_fields)
        self.assertEqual(result.telemetry.values["load_power"], 414)
        self.client.disconnect.assert_awaited_once()

    async def test_provisional_entity_is_disabled_without_opt_in_and_no_statistics(
        self,
    ):
        sample = await fetch_snapshot(object(), "AA:BB:CC:DD:EE:FF")
        coordinator = SimpleNamespace(
            data=sample,
            entry=SimpleNamespace(data={"address": "AA:BB:CC:DD:EE:FF"}),
            last_update_success=True,
        )
        for enabled in (False, True):
            entities = []
            await sensor.async_setup_entry(
                object(),
                SimpleNamespace(
                    runtime_data=coordinator,
                    data={"enable_provisional_sensors": enabled},
                ),
                entities.extend,
            )
            provisional = [e for e in entities if e.entity_description.provisional]
            self.assertEqual(len(provisional), 1)
            for entity in provisional:
                self.assertIsNone(entity.entity_description.state_class)
                self.assertEqual(
                    entity.entity_description.entity_registry_enabled_default, enabled
                )

    def test_setting_readbacks_are_optional_diagnostics_without_statistics(self):
        descriptions = {item.key: item for item in sensor.SENSORS}
        for key in capture.protocol.SETTINGS_KEYS:
            description = descriptions[key]
            self.assertFalse(description.entity_registry_enabled_default)
            self.assertEqual(description.entity_category, "diagnostic")
            self.assertIsNone(description.state_class)

    async def test_failed_read_makes_measurement_unavailable_and_health_off(self):
        sample = await fetch_snapshot(object(), "AA:BB:CC:DD:EE:FF")
        coordinator = SimpleNamespace(
            data=sample,
            entry=SimpleNamespace(data={"address": "AA:BB:CC:DD:EE:FF"}),
            last_update_success=False,
        )
        entity = sensor.XantrexSensor(coordinator, sensor.SENSORS[0])
        health = binary_sensor.XantrexReadHealth(coordinator)
        self.assertFalse(entity.available)
        self.assertTrue(health.available)
        self.assertFalse(health.is_on)

    def test_flow_is_registered(self):
        self.assertEqual(config_flow.XantrexConfigFlow.VERSION, 1)

    async def test_known_bluetooth_address_does_not_create_duplicate_discovery(self):
        flow = config_flow.XantrexConfigFlow()
        with patch.object(
            flow,
            "_async_current_entries",
            return_value=[SimpleNamespace(data={"address": "AA:BB:CC:DD:EE:FF"})],
        ):
            result = await flow.async_step_bluetooth(
                SimpleNamespace(address="aa:bb:cc:dd:ee:ff")
            )
        self.assertEqual(result["type"], "abort")
        self.assertEqual(result["reason"], "already_configured")

    def test_measurement_display_preserves_useful_precision(self):
        descriptions = {item.key: item for item in sensor.SENSORS}
        self.assertEqual(descriptions["battery_voltage"].suggested_display_precision, 2)
        self.assertEqual(descriptions["ac_voltage"].suggested_display_precision, 1)
        self.assertEqual(descriptions["ac_frequency"].suggested_display_precision, 1)
        self.assertEqual(descriptions["load_power"].suggested_display_precision, 0)
        self.assertEqual(descriptions["load_power"].native_unit_of_measurement, "W")
        self.assertEqual(
            descriptions["load_apparent_power"].native_unit_of_measurement, "VA"
        )
        self.assertEqual(descriptions["power_path"].device_class, "enum")

    def test_manifest_discovery_matchers_can_initialize_bluetooth(self):
        manifest = json.loads(
            (
                Path(__file__).parents[1]
                / "custom_components/xantrex_freedom_x_ble/manifest.json"
            ).read_text()
        )
        matchers = [
            dict(item, domain=manifest["domain"]) for item in manifest["bluetooth"]
        ]
        IntegrationMatcher(matchers).async_setup()


if __name__ == "__main__":
    unittest.main()
