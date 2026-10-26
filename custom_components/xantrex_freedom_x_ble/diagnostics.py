"""Export protocol samples without device identifiers."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry):
    coordinator = entry.runtime_data
    snapshot = coordinator.data
    return {
        "integration_version": "0.1.0",
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
    }
