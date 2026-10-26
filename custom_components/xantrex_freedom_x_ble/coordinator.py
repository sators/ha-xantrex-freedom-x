"""Bounded, periodic Bluetooth reads through Home Assistant's adapters."""

import asyncio
import logging
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from bleak import BleakClient
from bleak.exc import BleakError
from bleak_retry_connector import establish_connection

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL, DOMAIN
from .protocol import Identity, ProtocolError, Telemetry, read_identity, read_telemetry

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Snapshot:
    identity: Identity
    telemetry: Telemetry
    observed_at: datetime


async def fetch_snapshot(hass: HomeAssistant, address: str) -> Snapshot:
    """Connect, verify identity, read one complete sample, and release the panel.

    Use a new client for every connection. Never disconnect another app,
    force pairing, send writes, or keep the panel occupied between polls.
    """
    device = bluetooth.async_ble_device_from_address(hass, address, connectable=True)
    if device is None:
        raise BleakError(
            "No connectable Home Assistant adapter can currently see the remote"
        )
    client = None
    try:
        async with asyncio.timeout(40):
            client = await establish_connection(
                BleakClient,
                device,
                "Xantrex Freedom X Remote",
                max_attempts=2,
                timeout=15,
                pair=False,
            )
            identity = await read_identity(client)
            telemetry = await read_telemetry(client)
            return Snapshot(identity, telemetry, datetime.now(timezone.utc))
    finally:
        if client is not None:
            with suppress(BleakError, TimeoutError):
                async with asyncio.timeout(5):
                    await client.disconnect()


class XantrexCoordinator(DataUpdateCoordinator[Snapshot]):
    """Unavailable on read failure; never publish a previous reading as current."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
            ),
        )
        self.entry = entry

    async def _async_update_data(self) -> Snapshot:
        try:
            snapshot = await fetch_snapshot(self.hass, self.entry.data["address"])
            if snapshot.identity.serial != self.entry.data["serial"]:
                raise ProtocolError(
                    "The connected remote has a different serial number"
                )
            return snapshot
        except (BleakError, ProtocolError, TimeoutError, OSError) as err:
            raise UpdateFailed(str(err)) from err
