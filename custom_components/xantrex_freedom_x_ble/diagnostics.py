"""Export telemetry plus an on-demand read of custom protocol blocks."""

from bleak.exc import BleakError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry):
    coordinator = entry.runtime_data
    snapshot = coordinator.data
    capture = None
    try:
        fresh = await coordinator.async_capture_diagnostics()
        capture = {
            "observed_at": fresh.observed_at.isoformat(),
            "raw": fresh.telemetry.raw,
            "uint16_le": fresh.telemetry.words,
            "decoded": fresh.telemetry.values,
            "additional_fields": fresh.diagnostic_fields,
        }
    except (BleakError, ValueError, TimeoutError, OSError) as err:
        capture = {"error_type": type(err).__name__}
    return {
        "integration_version": "0.2.0",
        "manufacturer": snapshot.identity.manufacturer,
        "model": snapshot.identity.model,
        "address": "**REDACTED**",
        "serial": "**REDACTED**",
        "last_update_success": coordinator.last_update_success,
        "last_error_type": type(coordinator.last_exception).__name__
        if coordinator.last_exception
        else None,
        "last_successful_read": snapshot.observed_at.isoformat(),
        "decoded": snapshot.telemetry.values,
        "raw": snapshot.telemetry.raw,
        "uint16_le": snapshot.telemetry.words,
        "protocol_capture": capture,
    }
