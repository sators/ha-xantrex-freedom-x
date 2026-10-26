"""Confirm a readable Xantrex remote before creating any entities."""

import re
from typing import Any

import voluptuous as vol
from bleak.exc import BleakError

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS

from .const import CONF_POLL_INTERVAL, CONF_PROVISIONAL, DEFAULT_POLL_INTERVAL, DOMAIN
from .coordinator import fetch_snapshot
from .protocol import ProtocolError, UnsupportedDeviceError


class XantrexConfigFlow(ConfigFlow, domain=DOMAIN):
    """Manual address or Bluetooth discovery, followed by identity validation."""

    VERSION = 1

    def __init__(self) -> None:
        self._address = ""

    async def async_step_bluetooth(
        self, discovery_info: bluetooth.BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        self._address = discovery_info.address.upper()
        if any(
            entry.data.get(CONF_ADDRESS, "").upper() == self._address
            for entry in self._async_current_entries()
        ):
            return self.async_abort(reason="already_configured")
        # Deduplicate pending discovery flows before identity is read on submit.
        await self.async_set_unique_id(self._address)
        self.context["title_placeholders"] = {"name": "Xantrex Freedom X Remote"}
        return await self.async_step_user()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip().upper()
            if not re.fullmatch(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}", address):
                errors[CONF_ADDRESS] = "invalid_address"
            else:
                try:
                    snapshot = await fetch_snapshot(self.hass, address)
                except UnsupportedDeviceError:
                    errors["base"] = "unsupported_device"
                except ProtocolError:
                    errors["base"] = "unsupported_payload"
                except (BleakError, TimeoutError, OSError):
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(snapshot.identity.serial)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title="Xantrex Freedom X",
                        data={
                            **user_input,
                            CONF_ADDRESS: address,
                            "serial": snapshot.identity.serial,
                            "model": snapshot.identity.model,
                        },
                    )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS, default=self._address): str,
                    vol.Required(
                        CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL
                    ): vol.All(vol.Coerce(int), vol.Range(min=30, max=600)),
                    vol.Required(CONF_PROVISIONAL, default=False): bool,
                }
            ),
            errors=errors,
        )
