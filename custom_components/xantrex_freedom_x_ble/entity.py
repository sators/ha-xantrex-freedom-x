"""Shared Home Assistant device identity."""

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import XantrexCoordinator


class XantrexEntity(CoordinatorEntity[XantrexCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: XantrexCoordinator) -> None:
        super().__init__(coordinator)
        identity = coordinator.data.identity
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, identity.serial)},
            connections={(CONNECTION_BLUETOOTH, coordinator.entry.data["address"])},
            name="Xantrex Freedom X",
            manufacturer=identity.manufacturer,
            model=identity.model,
            serial_number=identity.serial,
        )
